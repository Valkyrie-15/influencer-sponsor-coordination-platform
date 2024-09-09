from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()  #database object


class users(db.Model):   # provide all propertires of database i.e CRUD
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True, autoincrement = True, nullable = False)
    username = db.Column(db.String , unique = True, nullable = False)
    email = db.Column(db.String , unique = True, nullable = False)
    password = db.Column(db.String , unique = True, nullable = False)
    user_type = db.Column(db.String , nullable = False)
    status = db.Column(db.String, nullable=False, default='Active')  


class sponsors(db.Model):
    __tablename__ = 'sponsors'

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    user_type = db.relationship("users", backref="sponsor")
    company_name = db.Column(db.String, nullable=False)
    industry_name = db.Column(db.String, nullable=False)

class influencers(db.Model):
    __tablename__ = 'influencers'

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    user_type = db.relationship("users", backref="influencer")
    name = db.Column(db.String, nullable=False)
    reach = db.Column(db.String, nullable=False)
    niche = db.Column(db.String, nullable=False)

class campaigns(db.Model):
    __tablename__ = 'campaigns'
    campaign_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsors.id'), nullable=False)
    camp_name = db.Column(db.String, nullable=False)
    camp_description = db.Column(db.String)
    camp_category = db.Column(db.String, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    prod_name = db.Column(db.String, nullable=False)
    prod_description = db.Column(db.String)
    ads_required = db.Column(db.Integer, nullable=False)  # New column
    budget = db.Column(db.Integer, nullable=False)
    visibility = db.Column(db.String(10), nullable=False, default='public')
    status = db.Column(db.String, nullable=False, default='Ongoing')
    

    

class adrequest(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.campaign_id'), nullable=False)
    campaign_name = db.Column(db.Text, nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('influencers.id'), nullable=False)
    ads_required = db.Column(db.Integer, nullable=False)  # New column
    ads_completed = db.Column(db.Integer, nullable=False, default=0)
    payment_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String, nullable=False, default='Pending')
    direction = db.Column(db.String, nullable=False)
    campaign = db.relationship('campaigns', foreign_keys=[campaign_id], backref=db.backref('ad_requests', lazy=True))
    influencer = db.relationship('influencers', foreign_keys=[influencer_id], backref=db.backref('ad_requests', lazy=True))


