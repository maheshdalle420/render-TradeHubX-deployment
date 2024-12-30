from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
import random
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tradehub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'juhayer.rahman@g.bracu.ac.bd'
app.config['MAIL_PASSWORD'] = 'hxbb ogzr utzw hcop'
app.config['MAIL_DEFAULT_SENDER'] = 'juhayer.rahman@g.bracu.ac.bd'

mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    profession = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    road = db.Column(db.String(200), nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    wallet_balance = db.Column(db.Float, default=0.0)
    tier = db.Column(db.String(50), default="None")
    email_notifications = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime, nullable=True)
    total_listings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)

    # Relationships
    listed_properties = db.relationship('Property', backref='seller', lazy=True)
    ratings_received = db.relationship('Rating', foreign_keys='Rating.rated_id', backref='seller', lazy=True)
    ratings_given = db.relationship('Rating', foreign_keys='Rating.rater_id', backref='buyer', lazy=True)

    def is_banned(self):
        """Check if the user is currently banned."""
        return self.banned_until and datetime.now() < self.banned_until

    def update_average_rating(self):
        """Calculate and update the user's average rating based on received ratings."""
        if self.ratings_received:
            total_rating = sum(rating.rating for rating in self.ratings_received)
            self.average_rating = total_rating / len(self.ratings_received)
        else:
            self.average_rating = 0.0
        db.session.commit()

    def update_wallet_balance(self, amount):
        """Add or subtract the specified amount from the user's wallet balance."""
        if self.wallet_balance + amount < 0:
            raise ValueError("Insufficient balance in the wallet.")
        self.wallet_balance += amount
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username} - Tier {self.tier}>'


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rated_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)




# Auction Cart Model
class AuctionCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    checkout_time_limit = db.Column(db.DateTime, nullable=False)  # Time limit for payment
    is_paid = db.Column(db.Boolean, default=False)

    property = db.relationship('Property', backref='auction_carts')  # Fetch property details easily

    def __repr__(self):
        return f'<AuctionCart User {self.user_id} Property {self.property_id} Paid {self.is_paid}>'



# Property Model
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    image_filename = db.Column(db.String(300), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    approved = db.Column(db.Boolean, default=False)
    winner_notified = db.Column(db.Boolean, default=False)
    user = db.relationship('User', foreign_keys=[user_id], backref='properties')
    is_paid = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Property {self.title}>'
# Wishlist Model
class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)

    def __repr__(self):
        return f'<Wishlist User {self.user_id} Property {self.property_id}>'



class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)
    auto_increment = db.Column(db.Float, nullable=True)  
    end_limit = db.Column(db.Float, nullable=True)  
    is_prioritized = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)
    user = db.relationship('User', backref='bids')
    notify_auction_end = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f'<Bid Property {self.property_id} User {self.user_id} Amount {self.bid_amount}>'

class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_name = db.Column(db.String(50), nullable=False)
    amount_earned = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

tier_subscription_cost= {'None': 0, 'Bronze': 1000, 'Silver': 3000, 'Gold': 5000}
wallet_limits = {'None': 1000, 'Bronze': 10000, 'Silver': 50000, 'Gold': 100000}
    

@app.route('/pay_for_auction/<int:property_id>', methods=['POST'])
def pay_for_auction(property_id):
    if 'user_id' not in session:
        flash('Please log in to complete your payment.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    auction = Property.query.get_or_404(property_id)
    highest_bid = Bid.query.filter_by(property_id=property_id).order_by(Bid.bid_amount.desc()).first()

    # Ensure the user is the winner
    if not highest_bid or highest_bid.user_id != user.id or auction.is_paid:
        flash('Unauthorized action or auction already paid.', 'danger')
        return redirect(url_for('auction_cart'))

    # Calculate payment
    discount = 0
    if user.tier == 'Silver':
        discount = highest_bid.bid_amount * 0.10
    elif user.tier == 'Gold':
        discount = highest_bid.bid_amount * 0.20

    total_amount = highest_bid.bid_amount - discount

    # Check wallet balance
    if user.wallet_balance < total_amount:
        flash(f'Insufficient wallet balance. You need ৳{total_amount - user.wallet_balance:.2f} more.', 'danger')
        return redirect(url_for('auction_cart'))

    # Deduct from buyer and credit to seller
    user.wallet_balance -= total_amount
    seller = User.query.get(auction.user_id)
    if seller:
        seller.wallet_balance += total_amount

    # Mark as paid
    auction.is_paid = True
    db.session.commit()

    flash(f'Payment successful! You saved ৳{discount:.2f}. Auction marked as paid.', 'success')
    return redirect(url_for('auction_receipt', property_id=property_id))


@app.route('/auction_receipt/<int:property_id>', methods=['GET', 'POST'])
def auction_receipt(property_id):
    if 'user_id' not in session:
        flash('Please log in to view your receipt.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    auction = Property.query.get_or_404(property_id)
    highest_bid = Bid.query.filter_by(property_id=property_id).order_by(Bid.bid_amount.desc()).first()

    # Ensure the user is the winner of the auction
    if not highest_bid or highest_bid.user_id != user.id or not auction.is_paid:
        flash('You are not authorized to view this receipt.', 'danger')
        return redirect(url_for('dashboard'))

    # Handle rating form submission
    if request.method == 'POST':
        rating = int(request.form['rating'])
        feedback = request.form['feedback']
        # Save rating and feedback in the database (assuming a `Rating` model exists)
        new_rating = Rating(
            rater_id=user.id,
            rated_id=auction.user_id,
            property_id=auction.id,
            rating=rating,
            feedback=feedback
        )
        db.session.add(new_rating)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('auction_receipt.html', auction=auction, highest_bid=highest_bid)



def schedule_auction_end_notification(user, property):
    """
    Schedule an email notification for when the auction is about to end.
    """
    time_remaining = property.end_time - datetime.now()
    if time_remaining.total_seconds() > 300:  
        notification_time = property.end_time - timedelta(minutes=5)
        
        send_auction_end_email(user, property, notification_time)

def send_auction_end_email(user, property, notification_time):
    """
    Send an email notification to the user about the auction ending soon.
    """
    subject = f"Reminder: Auction for '{property.title}' Ending Soon!"
    body = (f"Dear {user.full_name},\n\n"
            f"The auction for '{property.title}' is ending in less than 5 minutes.\n"
            f"Current highest bid: ৳{property.price}.\n\n"
            f"Don't miss your chance to bid!\n\n"
            f"Best regards,\n TradeHubX Team")
    msg = Message(subject, recipients=[user.email])
    msg.body = body

    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending auction end email: {e}")





@app.route('/update_notifications', methods=['POST'])
def update_notifications():
    if 'user_id' not in session:
        flash('Please log in to update your preferences.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    email_notifications = request.form.get('email_notifications') == 'true'
    user.email_notifications = email_notifications
    db.session.commit()

    flash('Your preferences have been updated.', 'success')
    return redirect(url_for('dashboard'))


def notify_users_before_auction_ends():
    soon_to_end = Property.query.filter(
        Property.end_time <= datetime.now() + timedelta(hours=1),
        Property.end_time > datetime.now()
    ).all()

    for property in soon_to_end:
        interested_users = AuctionCart.query.filter_by(property_id=property.id).join(User).all()
        for user in interested_users:
            if user.email_notifications:
                send_email_notification(user, property)

def send_email_notification(user, property):
    subject = f"Auction for {property.title} is Ending Soon!"
    body = f"Dear {user.username},\n\nThe auction for '{property.title}' will end in less than 1 hour. Don't miss the chance to place your bid!\n\nThank you,\nTradeHubX Team"
    msg = Message(subject, recipients=[user.email])
    msg.body = body
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

def notify_wishlist_items_going_live():
    soon_to_start = Property.query.filter(
        Property.start_time <= datetime.now() + timedelta(minutes=15),
        Property.start_time > datetime.now()
    ).all()

    for property in soon_to_start:
        wishlisted_users = Wishlist.query.filter_by(property_id=property.id).join(User).all()
        for wishlist in wishlisted_users:
            user = wishlist.user
            if user.tier == 'Gold':
                send_wishlist_notification(user, property)

def send_wishlist_notification(user, property):
    subject = f"Wishlist Alert: {property.title} is Going Live Soon!"
    body = f"Dear {user.username},\n\nThe item '{property.title}' in your wishlist is going live in less than 15 minutes. Get ready to bid!\n\nThank you,\nTradeHubX Team"
    msg = Message(subject, recipients=[user.email])
    msg.body = body
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending wishlist notification: {e}")


@app.route('/manage_tier')
def manage_tier():
    if 'user_id' not in session:
        flash('Please log in to manage your tier subscription.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('tier_management.html', user=user)
@app.route('/downgrade_tier/<new_tier>', methods=['POST'])
def downgrade_tier(new_tier):
    if 'user_id' not in session:
        flash('Please log in to manage your subscription.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    current_tier = user.tier
    valid_tiers = ["None", "Bronze", "Silver", "Gold"]

    if new_tier not in valid_tiers or valid_tiers.index(new_tier) >= valid_tiers.index(current_tier):
        flash('Invalid downgrade request. You cannot downgrade to a higher or same tier.', 'danger')
        return redirect(url_for('manage_tier'))

    refund_amount = tier_subscription_cost.get(current_tier, 0) - tier_subscription_cost.get(new_tier, 0)
    user.wallet_balance += refund_amount
    user.tier = new_tier

    db.session.commit()
    flash(f'Successfully downgraded to {new_tier} tier. Refund of ৳{refund_amount:.2f} has been added to your wallet.', 'success')
    return redirect(url_for('manage_tier'))


@app.route('/upgrade_tier/<new_tier>', methods=['POST'])
def upgrade_tier(new_tier):
    if 'user_id' not in session:
        flash('Please log in to manage your subscription.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    valid_tiers = ["None", "Bronze", "Silver", "Gold"]

    if new_tier not in valid_tiers or valid_tiers.index(new_tier) <= valid_tiers.index(user.tier):
        flash('Invalid upgrade request. You cannot upgrade to a lower or same tier.', 'danger')
        return redirect(url_for('manage_tier'))

    upgrade_cost = tier_subscription_cost[new_tier] - tier_subscription_cost[user.tier]

    if user.wallet_balance < upgrade_cost:
        flash(f'Insufficient balance for upgrading to {new_tier}. You need an additional ৳{upgrade_cost - user.wallet_balance:.2f}.', 'danger')
        return redirect(url_for('manage_tier'))

    user.wallet_balance -= upgrade_cost
    user.tier = new_tier

    db.session.commit()
    flash(f'Successfully upgraded to {new_tier} tier. Your wallet has been charged ৳{upgrade_cost:.2f}.', 'success')
    return redirect(url_for('manage_tier'))


@app.route('/subscribe_tier/<tier>', methods=['POST'])
def subscribe_tier(tier):
    if 'user_id' not in session:
        flash('Please log in to subscribe to a tier.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    valid_tiers = ["None", "Bronze", "Silver", "Gold"]

    if tier not in valid_tiers:
        flash('Invalid tier subscription request.', 'danger')
        return redirect(url_for('manage_tier'))

    cost = tier_subscription_cost.get(tier, 0)

    if user.wallet_balance < cost:
        flash(f'Insufficient balance. You need ৳{cost - user.wallet_balance:.2f} more to subscribe to {tier} tier.', 'danger')
        return redirect(url_for('manage_tier'))

    user.wallet_balance -= cost
    user.tier = tier
    db.session.commit()

    flash(f'Successfully subscribed to {tier} tier!', 'success')
    return redirect(url_for('manage_tier'))

@app.route('/wallet')
def wallet():
    if 'user_id' not in session:
        flash('Please log in to view your wallet.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    current_limit = wallet_limits.get(user.tier, wallet_limits["None"])

    # Ensure wallet balance does not exceed the current tier's limit
    if user.wallet_balance > current_limit:
        user.wallet_balance = current_limit
        db.session.commit()

    game_history = GameHistory.query.filter_by(user_id=user.id).order_by(GameHistory.timestamp.desc()).all()
    return render_template('wallet.html', user=user, game_history=game_history, wallet_limit=current_limit)
@app.route('/play_game', methods=['GET', 'POST'])
def play_game():
    if 'user_id' not in session:
        flash('Please log in to play games.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        try:
            earned_money = float(request.form['earned_money'])
            if earned_money > 0:
                # Apply tier-based bonus
                tier_bonus = {
                    "Bronze": 1.1,  # 10% bonus
                    "Silver": 1.3,  # 30% bonus
                    "Gold": 1.5   # 50% bonus
                }.get(user.tier, 1.0)

                total_earned = earned_money * tier_bonus
                user.wallet_balance += total_earned

                # Ensure wallet balance does not exceed the current tier's limit
                current_limit = wallet_limits.get(user.tier, wallet_limits["None"])
                if user.wallet_balance > current_limit:
                    user.wallet_balance = current_limit

                db.session.commit()

                # Log the reward in game history
                game_history = GameHistory(
                    user_id=user.id,
                    game_name="Snake Game",
                    amount_earned=total_earned
                )
                db.session.add(game_history)
                db.session.commit()

                flash(f'You earned ৳{total_earned:.2f} with your {user.tier} tier bonus! Wallet capped at ৳{current_limit}.', 'success')
        except ValueError:
            flash('Invalid reward amount.', 'danger')
        return redirect(url_for('wallet'))

    return render_template('play_game.html', user=user)
@app.route('/reward', methods=['POST'])
def reward():
    if 'user_id' not in session:
        flash('Please log in to claim your reward.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    game_name = request.form.get('game_name')
    earned_money = float(request.form.get('earned_money', 0))

    if earned_money > 0:
        user = User.query.get(user_id)
        if user:
            # Update wallet balance
            user.wallet_balance += earned_money
            db.session.commit()

            # Log the reward in game history
            game_history = GameHistory(user_id=user_id, game_name=game_name, amount_earned=earned_money)
            db.session.add(game_history)
            db.session.commit()

            flash(f'Congratulations! You earned ৳{earned_money:.2f} from {game_name.capitalize()}!', 'success')
        else:
            flash('User not found. Please try again.', 'danger')
    else:
        flash('No reward earned. Play the game to earn money!', 'warning')

    return redirect(url_for('wallet'))

@app.route('/rate_seller/<int:property_id>', methods=['GET', 'POST'])
def rate_seller(property_id):
    if 'user_id' not in session:
        flash('Please log in to rate the seller.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    property = Property.query.get_or_404(property_id)
    seller = User.query.get(property.user_id)

    if not property.is_paid:
        flash('You can only rate a seller after completing the payment.', 'danger')
        return redirect(url_for('auction_cart'))

    # Check if the user has already rated this seller for this property
    existing_rating = Rating.query.filter_by(rater_id=user.id, property_id=property_id).first()
    if existing_rating:
        flash('You have already rated this seller.', 'info')
        return redirect(url_for('auction_cart'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        feedback = request.form.get('feedback', '')

        # Create a new rating record
        new_rating = Rating(
            rater_id=user.id,
            rated_id=seller.id,
            property_id=property_id,
            rating=rating,
            feedback=feedback
        )
        db.session.add(new_rating)

        # Update the seller's average rating
        seller_ratings = Rating.query.filter_by(rated_id=seller.id).all()
        seller.average_rating = sum(r.rating for r in seller_ratings) / len(seller_ratings)

        db.session.commit()

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('auction_cart'))

    return render_template('rate_seller.html', property=property, seller=seller)


@app.route('/auction_cart', methods=['GET', 'POST'])
def auction_cart():
    if 'user_id' not in session:
        flash('Please log in to view your auction cart.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Fetch unpaid auctions where the user is the winner
    unpaid_auctions = Property.query.join(Bid).filter(
        Bid.user_id == user.id,
        Bid.property_id == Property.id,
        Property.is_paid == False,
        Property.end_time <= datetime.now()
    ).all()

    # Fetch paid auctions where the user has already completed payment
    paid_auctions = Property.query.join(Bid).filter(
        Bid.user_id == user.id,
        Bid.property_id == Property.id,
        Property.is_paid == True
    ).all()

    return render_template(
        'auction_cart.html',
        user=user,
        unpaid_auctions=unpaid_auctions,
        paid_auctions=paid_auctions
    )

@app.route('/bidding/<int:property_id>', methods=['GET', 'POST'])
def bidding(property_id):
    if 'user_id' not in session:
        flash('Please log in to place a bid.', 'warning')
        return redirect(url_for('login'))

    property = Property.query.get_or_404(property_id)
    user = User.query.get(session['user_id'])  # Get the current user

    # Check if the auction has ended
    now = datetime.now()
    if now >= property.end_time:
        flash('This auction has already ended. You cannot place a bid.', 'danger')
        return redirect(url_for('auctions'))

    if request.method == 'POST':
        try:
            bid_amount = float(request.form['bid_amount'])
            auto_increment = float(request.form['auto_increment']) if request.form.get('auto_increment') else None
            end_limit = float(request.form['end_limit']) if request.form.get('end_limit') else None
            is_prioritized = 'is_prioritized' in request.form
            notify_auction_end = 'notify_auction_end' in request.form and user.tier in ['Silver', 'Gold']  # Check if user is eligible

            # Fetch the current highest bid
            highest_bid = Bid.query.filter_by(property_id=property_id).order_by(Bid.bid_amount.desc()).first()

            # Ensure the bid is higher than the current highest bid
            if highest_bid and bid_amount <= highest_bid.bid_amount:
                flash('Your bid must be higher than the current highest bid.', 'danger')
                return redirect(url_for('bidding', property_id=property_id))

            # Create a new bid (manual or auto-bid)
            new_bid = Bid(
                property_id=property_id,
                user_id=session['user_id'],
                bid_amount=bid_amount,
                auto_increment=auto_increment if auto_increment and end_limit else None,
                end_limit=end_limit if auto_increment and end_limit else None,
                is_prioritized=is_prioritized,
                notify_auction_end=notify_auction_end
            )

            # Add the new bid to the database
            db.session.add(new_bid)
            db.session.commit()

            # If the user opted for notifications, schedule a notification
            if notify_auction_end:
                schedule_auction_end_notification(user, property)

            # Handle auto-bidding logic
            handle_auto_bidding(property_id, bid_amount)

            flash('Your bid has been placed successfully!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error placing bid: {e}', 'danger')


    # Fetch the current highest bid and all bids for the property
    highest_bid = Bid.query.filter_by(property_id=property_id).order_by(Bid.bid_amount.desc()).first()
    bids = Bid.query.filter_by(property_id=property_id).order_by(Bid.timestamp.desc()).all()

    return render_template('bidding.html', property=property, highest_bid=highest_bid, bids=bids, user=user)


    return render_template('bidding.html', property=property, highest_bid=highest_bid, bids=bids, user=user)
def handle_auto_bidding(property_id, explicit_bid_amount):
    """
    Handle auto-bidding for a property only when a competing bid surpasses the current highest bid.
    """
    while True:
        # Fetch the current highest bid
        highest_bid = Bid.query.filter_by(property_id=property_id).order_by(Bid.bid_amount.desc()).first()

        # Check for competing bids
        competing_bids = Bid.query.filter(
            Bid.property_id == property_id,
            Bid.auto_increment.isnot(None),
            Bid.end_limit > highest_bid.bid_amount,
            Bid.user_id != highest_bid.user_id  # Exclude the current highest bidder
        ).order_by(Bid.timestamp).all()

        if not competing_bids:  # Exit if no competing bids exist
            break

        placed_bid = False  # Track if any auto-bid is placed in this iteration

        for bid in competing_bids:
            next_bid_amount = highest_bid.bid_amount + bid.auto_increment

            # Place the auto-bid only if it doesn't exceed the user's end limit
            if next_bid_amount <= bid.end_limit:
                new_auto_bid = Bid(
                    property_id=property_id,
                    user_id=bid.user_id,
                    bid_amount=next_bid_amount,
                    auto_increment=bid.auto_increment,
                    end_limit=bid.end_limit,
                    is_prioritized=bid.is_prioritized
                )
                try:
                    db.session.add(new_auto_bid)
                    db.session.commit()

                    # Update the highest bid for the next iteration
                    highest_bid = new_auto_bid
                    placed_bid = True

                    # Notify prioritized users when they are outbid
                    if bid.is_prioritized:
                        send_prioritized_email(bid.user_id, property_id, "outbid")

                except Exception as e:
                    db.session.rollback()
                    print(f"Error placing auto-bid: {e}")

            # Notify if the user's limit has been exceeded
            if bid.is_prioritized and bid.end_limit <= highest_bid.bid_amount:
                send_prioritized_email(bid.user_id, property_id, "limit")

        # Exit the loop if no new bids were placed
        if not placed_bid:
            break
def send_prioritized_email(user_id, property_id, reason):
    user = User.query.get(user_id)
    property = Property.query.get(property_id)

    if user:
        if reason == "outbid":
            subject = 'Action Required: Your Priority Item'
            body = f"Dear {user.full_name},\n\nYour priority item '{property.title}' has been outbid. Place a higher bid to stay in the auction."
        elif reason == "limit":
            subject = 'Increase Your Bid Limit'
            body = f"Dear {user.full_name},\n\nYour priority item '{property.title}' has exceeded your bid limit. Increase your limit to stay in the auction."

        msg = Message(
            subject,
            recipients=[user.email],
            body=body
        )
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error sending prioritized email: {e}")

@app.route('/auctions')
def auctions():
    now = datetime.now()

    # Fetch all live auctions and order them by seller's average rating (highest first)
    live_properties = Property.query.join(User, Property.user_id == User.id).filter(
        Property.start_time <= now,
        Property.end_time > now,
        Property.approved == True
    ).order_by(User.average_rating.desc()).all()

    # Fetch all upcoming auctions
    upcoming_properties = Property.query.join(User, Property.user_id == User.id).filter(
        Property.start_time > now,
        Property.approved == True
    ).order_by(User.average_rating.desc()).all()

    # Fetch all past auctions
    past_properties = Property.query.join(User, Property.user_id == User.id).filter(
        Property.end_time <= now,
        Property.approved == True
    ).order_by(User.average_rating.desc()).all()

    past_with_winners = []
    for auction in past_properties:
        # Check if this auction has a winner
        highest_bid = Bid.query.filter_by(property_id=auction.id).order_by(Bid.bid_amount.desc()).first()
        winner = None
        if highest_bid:
            winner_user = User.query.get(highest_bid.user_id)
            winner = {
                'user': winner_user,
                'bid_amount': highest_bid.bid_amount
            }

            # Only send email to the latest winner of this auction if not already notified
            if winner_user.tier == "Gold" and not auction.winner_notified:
                try:
                    send_email_to_winner(winner_user, auction, highest_bid.bid_amount)
                    auction.winner_notified = True
                    db.session.commit()  # Mark the email as sent in the database
                except Exception as e:
                    print(f"Error sending email for auction {auction.id}: {e}")

        # Append auction details to the response
        past_with_winners.append({
            'auction': auction,
            'winner': winner,
            'email_sent': auction.winner_notified
        })

    return render_template(
        'auctions.html',
        live_properties=live_properties,
        upcoming_properties=upcoming_properties,
        past=past_with_winners
    )


def send_email_to_winner(user, auction, bid_amount):
    """
    Sends an email to the winner of the auction if they are a Gold member.
    """
    subject = f"Congratulations! You've won the auction for {auction.title}"
    body = (
        f"Dear {user.full_name},\n\n"
        f"Congratulations on winning the auction for '{auction.title}'! "
        f"Your winning bid was ৳{bid_amount}.\n\n"
        f"Thank you for being a Gold member.\n\n"
        f"Please proceed to complete the payment.\n\n"
        f"Best regards,\nTradeHubX"
    )
    msg = Message(subject, recipients=[user.email], body=body)
    mail.send(msg)

# Add to Wishlist Route
@app.route('/wishlist/add/<int:property_id>', methods=['POST'])
def add_to_wishlist(property_id):
    if 'user_id' not in session:
        flash('Please log in to add items to your wishlist.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing_entry = Wishlist.query.filter_by(user_id=user_id, property_id=property_id).first()

    if existing_entry:
        flash('This item is already in your wishlist.', 'info')
    else:
        new_wishlist_item = Wishlist(user_id=user_id, property_id=property_id)
        try:
            db.session.add(new_wishlist_item)
            db.session.commit()
            flash('Item added to your wishlist.', 'success')
        except Exception as e:
            flash(f'Error adding to wishlist: {str(e)}', 'danger')
            db.session.rollback()

    return redirect(url_for('auctions'))

# View Wishlist Route
@app.route('/wishlist')
def view_wishlist():
    if 'user_id' not in session:
        flash('Please log in to view your wishlist.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    wishlist_items = Wishlist.query.filter_by(user_id=user_id).all()
    properties = [Property.query.get(item.property_id) for item in wishlist_items]

    return render_template('wishlist.html', properties=properties)

# Remove from Wishlist Route
@app.route('/wishlist/remove/<int:property_id>', methods=['POST'])
def remove_from_wishlist(property_id):
    if 'user_id' not in session:
        flash('Please log in to manage your wishlist.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    wishlist_item = Wishlist.query.filter_by(user_id=user_id, property_id=property_id).first()

    if wishlist_item:
        try:
            db.session.delete(wishlist_item)
            db.session.commit()
            flash('Item removed from your wishlist.', 'success')
        except Exception as e:
            flash(f'Error removing from wishlist: {str(e)}', 'danger')
            db.session.rollback()
    else:
        flash('Item not found in your wishlist.', 'info')

    return redirect(url_for('view_wishlist'))


#created an admin
with app.app_context():
    def create_admin_user():
        admin_email = 'admin@example.com'
        admin_password = 'admin123'  # Replace with a secure password
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            hashed_password = generate_password_hash(admin_password)
            admin_user = User(
                full_name='Admin User',
                username='admin',
                email=admin_email,
                password=hashed_password,
                date_of_birth=datetime(2000, 1, 1),
                city='Admin City',
                area='Admin Area',
                road='Admin Road',
                
                is_verified=True,
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created: admin@example.com / admin123")
        else:
            print("Admin user already exists.")

    # Call the function during app initialization
    create_admin_user()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Query the database for the user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and if the password is correct
        if user and check_password_hash(user.password, password):
            if not user.is_verified:
                flash("Please verify your email before logging in.", 'warning')
                return redirect(url_for('login'))

            session['user_id'] = user.id  # Store user ID in session for login tracking

            # Check if the user is an admin
            if user.is_admin:
                session['admin_logged_in'] = True  # Set admin session
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin_panel'))  # Redirect admin to the admin panel

            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))  # Redirect to user dashboard

        else:
            flash('Invalid login credentials!', 'danger')

    return render_template('login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    pending_properties = Property.query.filter_by(approved=False).all()
    active_auctions = Property.query.filter(
        Property.approved == True,
        Property.start_time <= datetime.now(),
        Property.end_time > datetime.now()
    ).all()

    auction_details = []
    for auction in active_auctions:
        current_bid = Bid.query.filter_by(property_id=auction.id).order_by(Bid.bid_amount.desc()).first()

        # Count unique users, excluding auto-bidding increments
        active_users = Bid.query.filter(
            Bid.property_id == auction.id,
            Bid.auto_increment.is_(None)
        ).distinct(Bid.user_id).count()

        auction_details.append({
            'auction': auction,
            'current_bid': current_bid.bid_amount if current_bid else 'No bids',
            'active_users': active_users
        })

    users = User.query.all()

    return render_template('admin_panel.html', properties=pending_properties, auction_details=auction_details, users=users)

@app.route('/admin/approve/<int:id>', methods=['POST'])
def approve_auction(id):
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    property = Property.query.get_or_404(id)
    action = request.form.get('action')
    if action == 'approve':
        property.approved = True
        db.session.commit()
        flash(f'Property "{property.title}" approved.', 'success')
    elif action == 'reject':
        db.session.delete(property)
        db.session.commit()
        flash(f'Property "{property.title}" rejected and removed.', 'info')

    return redirect(url_for('admin_panel'))

# Manage Users (Ban/Delete)
@app.route('/admin/manage_users', methods=['POST'])
def manage_users():
    if not session.get('admin_logged_in'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('login'))

    action = request.form.get('action')
    user_id = request.form.get('user_id')
    user = User.query.get_or_404(user_id)

    if action == 'ban':
        ban_duration = int(request.form.get('ban_duration', 0))
        user.banned_until = datetime.now() + timedelta(hours=ban_duration)
        db.session.commit()
        flash(f'User {user.username} has been banned for {ban_duration} hours.', 'success')
    elif action == 'delete':
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')

    return redirect(url_for('admin_panel'))


@app.route('/create_listing', methods=['GET', 'POST'])
def create_listing():
    if 'user_id' not in session:
        flash('Please log in to create a listing.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])  # Ensure the user is retrieved

    # Listing costs and free listing thresholds
    tier_costs = {'None': 3000, 'Bronze': 2000, 'Silver': 1000, 'Gold': 500}
    free_listing_threshold = {'Bronze': 10, 'Silver': 5, 'Gold': 3}

    current_cost = tier_costs[user.tier]
    free_listing = False

    # Calculate free listing eligibility
    if user.tier in free_listing_threshold:
        threshold = free_listing_threshold[user.tier]
        if (Property.query.filter_by(user_id=user.id).count() + 1) % threshold == 0:
            current_cost = 0
            free_listing = True

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        location = request.form['location']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        image = request.files['image']

        # Parse the start_time and end_time strings into datetime objects
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format. Please use YYYY-MM-DD HH:MM.', 'danger')
            return redirect(url_for('create_listing'))

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
        else:
            filename = None

        # Check user's wallet balance
        if current_cost > 0 and user.wallet_balance < current_cost:
            flash(f'Insufficient wallet balance. You need ৳{current_cost - user.wallet_balance:.2f} more.', 'danger')
            return redirect(url_for('create_listing'))

        # Deduct the listing fee from wallet balance
        if current_cost > 0:
            user.wallet_balance -= current_cost

        new_property = Property(
            user_id=user.id,
            title=title,
            description=description,
            price=float(price),
            location=location,
            start_time=start_time,
            end_time=end_time,
            image_filename=filename
        )

        try:
            db.session.add(new_property)
            db.session.commit()
            flash('Property listing created successfully!', 'success')
            return redirect(url_for('view_listings'))
        except Exception as e:
            flash(f'Error creating listing: {e}', 'danger')
            db.session.rollback()

    return render_template(
        'create_listing.html',
        user=user,
        tier=user.tier,
        wallet_balance=user.wallet_balance,
        listing_cost=current_cost,
        is_free=free_listing
    )

@app.route('/seller_dashboard')
def seller_dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the seller dashboard.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Fetch seller ratings
    ratings = Rating.query.filter_by(rated_id=user.id).all()
    average_rating = round(sum(r.rating for r in ratings) / len(ratings), 1) if ratings else None
    feedbacks = [{'rating': r.rating, 'feedback': r.feedback, 'timestamp': r.timestamp} for r in ratings]

    return render_template(
        'seller_dashboard.html',
        user=user,
        average_rating=average_rating,
        feedbacks=feedbacks
    )

@app.route('/view_live_auctions')
def view_live_auctions():
    if 'user_id' not in session:
        flash('Please log in to view your live auctions.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    now = datetime.now()

    # Fetch live auctions with bid counts
    live_auctions = Property.query.filter(
        Property.user_id == user.id,
        Property.start_time <= now,
        Property.end_time > now
    ).all()

    live_auction_details = []
    for auction in live_auctions:
        bid_count = Bid.query.filter_by(property_id=auction.id).count()
        live_auction_details.append({
            'auction': auction,
            'bid_count': bid_count
        })

    return render_template('live_auctions.html', live_auction_details=live_auction_details)

@app.route('/view_sold_auctions')
def view_sold_auctions():
    if 'user_id' not in session:
        flash('Please log in to view your sold auctions.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Fetch sold auctions with payment status and winner details
    sold_auctions = Property.query.filter(
        Property.user_id == user.id,
        Property.end_time <= datetime.now()
    ).all()

    sold_auction_details = []
    for auction in sold_auctions:
        highest_bid = Bid.query.filter_by(property_id=auction.id).order_by(Bid.bid_amount.desc()).first()
        winner = User.query.get(highest_bid.user_id) if highest_bid else None
        sold_auction_details.append({
            'auction': auction,
            'is_paid': auction.is_paid,
            'winner': winner,
            'winning_bid': highest_bid.bid_amount if highest_bid else None
        })

    return render_template('sold_auctions.html', sold_auction_details=sold_auction_details)

@app.route('/buyer_dashboard')
def buyer_dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the buyer dashboard.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Check for the latest unpaid auction won by the user
    won_auction = Property.query.join(Bid).filter(
        Bid.user_id == user.id,
        Bid.property_id == Property.id,
        Property.is_paid == False,
        Property.end_time < datetime.now()
    ).order_by(Property.end_time.desc()).first()

    return render_template('buyer_dashboard.html', user=user, won_auction=won_auction)

@app.route('/update_listing/<int:id>', methods=['GET', 'POST'])
def update_listing(id):
    if 'user_id' not in session:
        flash('Please log in to update your listing.', 'warning')
        return redirect(url_for('login'))

    property = Property.query.get_or_404(id)

    # Ensure that the logged-in user owns the property
    if property.user_id != session['user_id']:
        flash('You are not authorized to edit this listing.', 'danger')
        return redirect(url_for('view_listings'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        location = request.form['location']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        image = request.files['image']

        # Convert start_time and end_time to datetime objects
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format. Please use YYYY-MM-DD HH:MM.', 'danger')
            return redirect(url_for('update_listing', id=id))

        property.title = title
        property.description = description
        property.price = float(price)
        property.location = location
        property.start_time = start_time
        property.end_time = end_time

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            property.image_filename = filename

        try:
            db.session.commit()
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('view_listings'))
        except Exception as e:
            flash(f'Error updating listing: {e}', 'danger')
            db.session.rollback()

    return render_template('update_listing.html', property=property)

@app.route('/delete_listing/<int:id>', methods=['POST'])
def delete_listing(id):
    if 'user_id' not in session:
        flash('Please log in to delete your listing.', 'warning')
        return redirect(url_for('login'))

    property = Property.query.get_or_404(id)

    # Ensure that the logged-in user owns the property
    if property.user_id != session['user_id']:
        flash('You are not authorized to delete this listing.', 'danger')
        return redirect(url_for('view_listings'))

    try:
        if property.image_filename:
            # If there's an image associated, delete it from the file system
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], property.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(property)
        db.session.commit()
        flash('Property listing deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting listing: {e}', 'danger')
        db.session.rollback()

    return redirect(url_for('view_listings'))

@app.route('/listings')
def view_listings():
    properties = Property.query.all()
    return render_template('view_listings.html', properties=properties)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Get updated data from the form
        user.full_name = request.form.get('full_name', user.full_name)
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)

        # Convert date_of_birth to a datetime.date object if provided
        date_of_birth_str = request.form.get('date_of_birth')
        if date_of_birth_str:
            try:
                user.date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('update_profile'))

        user.profession = request.form.get('profession', user.profession)
        user.city = request.form.get('city', user.city)
        user.area = request.form.get('area', user.area)
        user.road = request.form.get('road', user.road)

        # Validate email uniqueness
        if User.query.filter(User.email == user.email, User.id != user.id).first():
            flash('This email is already in use.', 'danger')
            return redirect(url_for('update_profile'))

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
            db.session.rollback()

    return render_template('update_profile.html', user=user)

#Forgot password route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email.', 'danger')
            return redirect(url_for('forgot_password'))

        # Generate OTP and expiry
        otp = str(random.randint(100000, 999999))
        otp_expiry = datetime.now() + timedelta(minutes=10)

        user.otp = otp
        user.otp_expiry = otp_expiry
        db.session.commit()

        # Send OTP email
        send_otp_email(user.email, otp)
        flash('An OTP has been sent to your email for password reset.', 'info')
        return redirect(url_for('reset_password', id=user.id))

    return render_template('forgot_password.html')

# Reset password route
@app.route('/reset_password/<int:id>', methods=['GET', 'POST'])
def reset_password(id):
    user = User.query.get(id)

    if not user:
        return "User not found!", 404

    if request.method == 'POST':
        entered_otp = request.form['otp']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', id=id))

        if entered_otp == user.otp and datetime.now() < user.otp_expiry:
            user.password = generate_password_hash(new_password)
            user.otp = None
            user.otp_expiry = None
            db.session.commit()

            flash('Password reset successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired OTP!', 'danger')

    return render_template('reset_password.html', id=id)

# Change password in dashboard route
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not check_password_hash(user.password, current_password):
            flash('Current password is incorrect!', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('change_password'))

        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('change_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get the form data
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        date_of_birth_str = request.form.get('date_of_birth')
        profession = request.form.get('profession')
        city = request.form.get('city')
        area = request.form.get('area')
        road = request.form.get('road')

        # Validate inputs
        if not all([full_name, username, email, password, confirm_password, date_of_birth_str, city, area, road]):
            flash('All fields except profession are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        try:
            date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        # Create new user object
        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            password=hashed_password,
            date_of_birth=date_of_birth,
            profession=profession,
            city=city,
            area=area,
            road=road
        )

        # Add the user to the database
        try:
            db.session.add(new_user)
            db.session.commit()

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            otp_expiry = datetime.now() + timedelta(minutes=10)

            new_user.otp = otp
            new_user.otp_expiry = otp_expiry
            db.session.commit()

            # Send OTP
            send_otp_email(new_user.email, otp)

            flash('An OTP has been sent to your email for verification.', 'info')
            return redirect(url_for('verify_otp', id=new_user.id))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'danger')
            db.session.rollback()

    return render_template('register.html')

# Send OTP email function
def send_otp_email(email, otp):
    msg = Message('Your OTP for Email Verification',
                  recipients=[email])
    msg.body = f'Your OTP is: {otp}. It is valid for 10 minutes.'
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

# OTP Verification route
@app.route('/verify_otp/<int:id>', methods=['GET', 'POST'])
def verify_otp(id):
    user = User.query.get(id)

    if not user:
        return "User not found!", 404

    if request.method == 'POST':
        entered_otp = request.form['otp']

        # Check if OTP matches and is within the expiry time (10 minutes)
        if entered_otp == user.otp:
            if datetime.now() < user.otp_expiry:  # Check if OTP is not expired
                user.is_verified = True  # Mark the email as verified
                db.session.commit()
                flash('Email successfully verified!', 'success')
                return redirect(url_for('login'))  # Redirect to login page after successful verification
            else:
                flash("OTP has expired!", 'danger')  # OTP expired
        else:
            flash("Invalid OTP!", 'danger')  # OTP mismatch

    return render_template('verify_otp.html', id=user.id)

# Login route

# Dashboard route (Protected by login)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to view your dashboard.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    # Calculate the wallet limit dynamically based on user's tier
    wallet_limit = {
        'None': 1000,
        'Bronze': 10000,
        'Silver': 50000,
        'Gold': 100000
    }.get(user.tier, 1000)

    return render_template(
        'dashboard.html',
        user=user,
        wallet_limit=wallet_limit,
        tier_subscription_cost=tier_subscription_cost
    )

@app.route('/logout')
def logout():
    # Clear the session to log the user out
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# Ensure that the database tables are created within the application context
with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

# Run the Flask app
if __name__ == '__main__':
    app.run()
