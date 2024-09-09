from flask_restful import Resource
from flask import flash, redirect, url_for

from model import *

class FlagUserAPI(Resource):
    def post(self, user_id):
        # Checking for valid user ID
        user = users.query.get(user_id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Checking if user is already flagged
        if user.status == 'Flagged':
            flash('User already flagged.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Flag the user
        user.status = 'Flagged'
        db.session.commit()

        flash('User flagged successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

class FlagCampaignAPI(Resource):
    def post(self, campaign_id):
        campaign = campaigns.query.get(campaign_id)
        if not campaign:
            flash('Campaign not found.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Checking if campaign is already flagged
        if campaign.status == 'Flagged':
            flash('Campaign already flagged.', 'warning')
            return redirect(url_for('admin_dashboard'))

        # Flag the campaign and stop it immediately
        campaign.status = 'Flagged'
        db.session.commit()

        flash('Campaign flagged successfully and stopped.', 'success')
        return redirect(url_for('admin_dashboard'))

    

