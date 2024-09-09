from functools import wraps
from flask import Flask, request as rq , render_template as rt, redirect as rd, url_for as uf, flash, session, jsonify
from model import *      # * => everything 
from api import *
import os
import random
from datetime import datetime 
from flask_restful import Api

current_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(current_dir, 'mad-1.sqlite3')
app.config["SECRET_KEY"] = "your_secret_key"

db.init_app(app)
app.app_context().push()  # maintains queues of rqs that come to the app (manages the traffic)
api = Api(app)
# Import the API resources
from api import FlagUserAPI, FlagCampaignAPI

# Add the resources to the API
api.add_resource(FlagUserAPI, '/api/flag/user/<int:user_id>')
api.add_resource(FlagCampaignAPI, '/api/flag/campaign/<int:campaign_id>')




def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to login first.')
            return rd(uf('home'))
        return func(*args, **kwargs)
    return inner


# Route for home page and login
@app.route('/', methods=['GET', 'POST'])
def home():
    if rq.method == 'POST':
        username = rq.form['username']
        email = rq.form['email']
        password = rq.form['password']

        user = users.query.filter_by(username=username, email=email, password=password).first()
        if user:
            if user.status == 'Flagged':  # Check if the user is flagged
                session['user_id'] = user.id
                return rd(uf('flagged_dashboard'))  # Redirect to flagged dashboard
            
            session['user_id'] = user.id  # Store user ID in session
            session['username'] = username
            
            if user.user_type == 'admin':
                session['role'] = 'admin'
                return rd(uf('admin_dashboard'))
            elif user.user_type == 'sponsor':
                session['role'] = 'sponsor'
                return rd(uf('sponsor_dashboard'))
            elif user.user_type == 'influencer':
                session['role'] = 'influencer'
                return rd(uf('influencer_dashboard'))
        else:
            flash('Invalid username, email, or password.')  # Flash message for invalid credentials
    
    return rt('home.html')



@app.route('/flagged_dashboard')
def flagged_dashboard():
    return rt('flagged_dashboard.html')


######################### admin related routes ###########################


@app.route('/admin_dashboard')
@auth_required
def admin_dashboard():
    try:
        ongoing_campaigns = db.session.query(
            campaigns.campaign_id,
            campaigns.camp_name,
            db.func.coalesce(db.func.sum(adrequest.ads_completed), 0).label('ads_completed'),
            db.func.coalesce(db.func.sum(adrequest.ads_required), 0).label('ads_required'),
            campaigns.camp_category,
            campaigns.camp_description,
            campaigns.prod_name,
            campaigns.prod_description,
            campaigns.start_date,
            campaigns.end_date,
            campaigns.budget,
            campaigns.status,
            campaigns.visibility
        ).join(adrequest, adrequest.campaign_id == campaigns.campaign_id)\
         .filter(campaigns.status == 'Ongoing')\
         .group_by(campaigns.campaign_id).all()

        flagged_users = users.query.filter_by(status='Flagged').all()
        flagged_campaigns = campaigns.query.filter_by(status='Flagged').all()

        
        return rt('admin_dashboard.html',
                  ongoing_campaigns=ongoing_campaigns,
                  flagged_users=flagged_users,
                  flagged_campaigns=flagged_campaigns)
    except Exception as e:
        print("Error:", e)
        return "An error occurred while retrieving data."



@app.route('/admin_info')
@auth_required
def admin_info():
    all_sponsors = sponsors.query.join(users, users.id == sponsors.id).add_columns(
        users.id, users.username, users.email, sponsors.company_name, sponsors.industry_name
    ).all()
    
    all_influencers = influencers.query.join(users, users.id == influencers.id).add_columns(
        users.id, users.username, users.email, influencers.name, influencers.reach, influencers.niche
    ).all()
    
    all_campaigns = campaigns.query.join(sponsors, sponsors.id == campaigns.sponsor_id).add_columns(
        campaigns.campaign_id, campaigns.camp_name, campaigns.camp_description, campaigns.camp_category, 
        campaigns.start_date, campaigns.end_date, campaigns.prod_name, 
        campaigns.prod_description, campaigns.ads_required, campaigns.budget, 
        campaigns.visibility, campaigns.status, sponsors.company_name
    ).all()
    
    return rt('admin_info.html', sponsors=all_sponsors, influencers=all_influencers, campaigns=all_campaigns)





@app.route('/unflag_campaign/<int:campaign_id>', methods=['POST'])
@auth_required
def unflag_campaign(campaign_id):
    campaign = campaigns.query.get(campaign_id)
    if campaign:
        campaign.status = 'Ongoing'
        db.session.commit()
        flash('Campaign unflagged successfully', 'success')
    return redirect(url_for('admin_dashboard'))




@app.route('/unflag_user/<int:user_id>', methods=['POST'])
@auth_required
def unflag_user(user_id):
    user = users.query.get(user_id)
    if user:
        user.status = 'Active'
        db.session.commit()
        flash('User unflagged successfully', 'success')
    return redirect(url_for('admin_dashboard'))




@app.route('/admin_stats', methods=['GET'])
@auth_required
def admin_stats():
    return rt('admin_stats.html')




@app.route('/search_admin', methods=['POST'])
@auth_required
def admin_search():
    search_type = rq.form.get('search_tag')  # Make sure the form field names are correct
    query = rq.form.get('search_query')

    print(f"Search Type: {search_type}, Query: {query}")  # Debugging line

    data = []

    if search_type == 'sponsor':
        data = db.session.query(users, sponsors).join(sponsors).filter(users.username.ilike(f'%{query}%')).all()
        print(f"Sponsor Data: {data}")  # Debugging line

    elif search_type == 'campaign':
        data = campaigns.query.filter(campaigns.camp_name.ilike(f'%{query}%')).all()
        print(f"Campaign Data: {data}")  # Debugging line

    elif search_type == 'influencer':
        data = db.session.query(users, influencers).join(influencers).filter(users.username.ilike(f'%{query}%')).all()
        print(f"Influencer Data: {data}")  # Debugging line

    return rt('admin_search_results.html', search_type=search_type, search_data=data)





@app.route('/get_data', methods=['GET'])

def get_data():
    sponsor_data = users.query.filter_by(user_type='sponsor').all()
    data_dict = dict()
    sponsor_name = []
    campaign_count = []
    bar_color = []

    for sponsor in sponsor_data:
        sponsor_name.append(sponsor.username)
        
        # Get the campaign count for each specific sponsor
        count = campaigns.query.filter_by(sponsor_id=sponsor.id).count()
        campaign_count.append(count)

        r = random.randint(0,255)
        g = random.randint(0,255)
        b = random.randint(0,255)

        bar_color.append(f'rgb({r},{g},{b})')
    
    data_dict['sponsor'] = sponsor_name
    data_dict['campaign'] = campaign_count
    data_dict['color'] = bar_color

    return jsonify(data_dict)


@app.route('/get_influencer_data', methods=['GET'])
def get_influencer_data():
    influencer_data = users.query.filter_by(user_type='influencer').all()
    data_dict = dict()
    influencer_name = []
    accepted_campaign_count = []
    bar_color = []

    for influencer in influencer_data:
        influencer_name.append(influencer.username)
        
        # Get the accepted campaign count for each specific influencer from the adrequest table
        count = adrequest.query.filter_by(influencer_id=influencer.id, status='Accepted').count()
        accepted_campaign_count.append(count)

        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)

        bar_color.append(f'rgb({r},{g},{b})')

        print(f"Influencer: {influencer.username}, Accepted Campaigns: {count}")
    
    data_dict['influencer'] = influencer_name
    data_dict['accepted_campaigns'] = accepted_campaign_count
    data_dict['color'] = bar_color

    return jsonify(data_dict)


@app.route('/get_user_counts', methods=['GET'])
def get_user_counts():
    sponsor_count = users.query.filter_by(user_type='sponsor').count()
    influencer_count = users.query.filter_by(user_type='influencer').count()
    bar_color = []

    # Generate random colors for each user type
    for _ in range(2):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        bar_color.append(f'rgb({r},{g},{b})')

    data_dict = {
        'user_types': ['Sponsors', 'Influencers'],
        'counts': [sponsor_count, influencer_count],
        'color': bar_color
    }

    return jsonify(data_dict)




@app.route('/get_ongoing_campaigns_data', methods=['GET'])
def get_ongoing_campaigns_data():
    from sqlalchemy import func

    # Fetch the count of ongoing campaigns
    ongoing_campaigns_count = campaigns.query.filter_by(status='Ongoing').count()

    # Fetch the count of ad requests sent by sponsors
    ad_requests_sent_by_sponsors = db.session.query(
        func.count(adrequest.id)
    ).filter(adrequest.direction == 'to_influencer').scalar()

    # Fetch the count of ad requests sent by influencers
    ad_requests_sent_by_influencers = db.session.query(
        func.count(adrequest.id)
    ).filter(adrequest.direction == 'to_sponsor').scalar()

    data_dict = {
        'labels': ['Ongoing Campaigns'],
        'campaigns_count': [ongoing_campaigns_count],
        'ad_requests_sent_by_sponsors': [ad_requests_sent_by_sponsors],
        'ad_requests_sent_by_influencers': [ad_requests_sent_by_influencers]
    }

    return jsonify(data_dict)


@app.route('/get_campaigns_stats', methods=['GET'])
def get_campaigns_stats():
    # Query the number of public campaigns
    public_campaigns_count = db.session.query(campaigns).filter(campaigns.visibility == 'public').count()
    
    # Query the number of private campaigns
    private_campaigns_count = db.session.query(campaigns).filter(campaigns.visibility == 'private').count()

    data_dict = {
        'labels': ['Public Campaigns', 'Private Campaigns'],
        'data': [public_campaigns_count, private_campaigns_count]
    }

    return jsonify(data_dict)



@app.route('/get_flagged_vs_other_campaigns', methods=['GET'])
def get_flagged_vs_other_campaigns():
    # Get the count of flagged campaigns
    flagged_campaigns_count = campaigns.query.filter_by(status='Flagged').count()
    
    # Get the count of other campaigns
    other_campaigns_count = campaigns.query.filter(campaigns.status != 'Flagged').count()
    
    data_dict = {
        'labels': ['Flagged Campaigns', 'Other Campaigns'],
        'data': [flagged_campaigns_count, other_campaigns_count],
        'colors': ['rgb(255, 99, 132)', 'rgb(75, 192, 192)']
    }
    
    return jsonify(data_dict)




####################### sponsor related routes #############################


@app.route('/sponsor_signup', methods = ['GET','POST'])

def sponsor_signup():
    if rq.method == 'POST':
        email = rq.form['email']
            

        if not users.query.filter(users.email == email).all():
            newuser = users(username = rq.form['username'] , email = rq.form['email'], password = rq.form['password'] , user_type = rq.form['type'])
            db.session.add(newuser)
            db.session.commit()

            session['username'] = newuser.username

            new_sponsor = sponsors(id=newuser.id, company_name=rq.form['company_name'], industry_name=rq.form['industry_name'])
            db.session.add(new_sponsor) 
            db.session.commit()
            flash('Sponsor account created successfully!')
        return rd('/')
    return rt('sponsor_signup.html')



@app.route('/sponsor_dashboard', methods=['GET', 'POST'])
@auth_required
def sponsor_dashboard():
    if session.get('role') != 'sponsor':
        flash('Unauthorized access.', 'danger')
        return rd(uf('home'))

    username = session.get('username')
    sponsor_id = session.get('user_id')

    user = users.query.get(sponsor_id)

    if sponsor_id is None:
        flash('You must be logged in to view your dashboard.', 'warning')
        return rd(uf('home'))  # Redirect to home page

    if user.status == 'Flagged':
        return rt('flagged_dashboard.html', user=user)

    # Query for existing campaigns based on sponsor ID
    existing_campaigns = campaigns.query.filter_by(sponsor_id=sponsor_id).all()

    # Calculate progress for each campaign
    campaign_data = []
    for campaign in existing_campaigns:
        ad_requests = adrequest.query.filter_by(campaign_id=campaign.campaign_id).all()
        total_ads = campaign.ads_required
        completed_ads = sum(request.ads_completed for request in ad_requests if request.status == 'Accepted')
        progress = (completed_ads / total_ads) * 100 if total_ads else 0
        campaign_data.append({
            'campaign': campaign,
            'ads_completed': completed_ads,
            'progress': progress
        })

    return rt('sponsor_dashboard.html', username=username, campaign_data=campaign_data)


# Route for new campaign creation
@app.route('/new_campaign', methods=['GET', 'POST'])
@auth_required
def new_campaign():
    if rq.method == 'GET':
        return rt('new_campaign.html')
    elif rq.method == 'POST':
        # Retrieve current user's ID from session
        user_id = session.get('user_id')
        if user_id is None:
            flash('You must be logged in to create a campaign.')
            return rd(uf('home'))

        # Retrieve form data
        camp_name = rq.form['camp_name']
        camp_desc = rq.form['camp_desc']
        category = rq.form['category']
        start_date = datetime.strptime(rq.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(rq.form['end_date'], '%Y-%m-%d').date()
        prod_name = rq.form['prod_name']
        prod_desc = rq.form['prod_desc']
        ads_required = rq.form['ads_required']
        budget = rq.form['budget']
        visibility = rq.form['visibility']  # Retrieve visibility from form

        # Create new Campaign object
        new_campaign = campaigns(
            sponsor_id=user_id,
            camp_name=camp_name,
            camp_description=camp_desc,
            camp_category=category,
            start_date=start_date,
            end_date=end_date,
            prod_name=prod_name,
            prod_description=prod_desc,
            ads_required = ads_required,
            budget=budget,
            visibility=visibility  # Set visibility
        )

        # Add and commit to database
        db.session.add(new_campaign)
        db.session.commit()

        flash('New campaign created successfully!','success')
        return rd(uf('sponsor_dashboard'))



# route to editing a campaign
@app.route('/edit_campaign/<int:campaign_id>', methods=['GET', 'POST'])
@auth_required
def edit_campaign(campaign_id):
    campaign = campaigns.query.get_or_404(campaign_id)

    if rq.method == 'POST':
        campaign.camp_name = rq.form['camp_name']
        campaign.camp_description = rq.form['camp_desc']
        campaign.camp_category = rq.form['category']
        campaign.start_date = datetime.strptime(rq.form['start_date'], '%Y-%m-%d').date()
        campaign.end_date = datetime.strptime(rq.form['end_date'], '%Y-%m-%d').date()
        campaign.prod_name = rq.form['prod_name']
        campaign.prod_description = rq.form['prod_desc']
        campaign.budget = rq.form['budget']
        campaign.visibility = rq.form['visibility'] 
        db.session.commit()
        flash('Campaign updated successfully!', 'success')
        return rd(uf('sponsor_dashboard'))

    return rt('edit_campaign.html', campaign=campaign)



# route for deleting a campaign
@app.route('/delete_campaign/<int:campaign_id>', methods=['POST'])
@auth_required
def delete_campaign(campaign_id):
    campaign = campaigns.query.get_or_404(campaign_id)
    
    # Delete related ad requests
    related_adrequests = adrequest.query.filter_by(campaign_id=campaign_id).all()
    for req in related_adrequests:
        db.session.delete(req)
    
    db.session.delete(campaign)
    db.session.commit()
    flash('Campaign and its related ad requests deleted successfully!', 'success')
    return rd(uf('sponsor_dashboard'))



# route to sponsor profile
@app.route('/sponsor_profile')
@auth_required
def sponsor_profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('You must be logged in to view your profile.', 'warning')
        return rd(uf('home'))

    sponsor = sponsors.query.filter_by(id=user_id).first()
    user = users.query.filter_by(id=user_id).first()
    if not sponsor:
        flash('Sponsor profile not found.', 'error')
        return rd(uf('home'))

    return rt('sponsor_profile.html', sponsor=sponsor, user = user)



@app.route('/search_influencer', methods=['GET', 'POST'])
@auth_required
def search_influencer():
    sponsor_id = session.get('user_id')
    ongoing_campaigns = campaigns.query.filter_by(sponsor_id=sponsor_id).all()

    if rq.method == 'POST':
        search_tag = rq.form.get('search_tag')
        query = rq.form.get('search_query')

        # Ensure query is case-insensitive
        if search_tag == 'name':
            data = influencers.query.filter(influencers.name.ilike(f'%{query}%')).all()
        elif search_tag == 'niche':
            data = influencers.query.filter(influencers.niche.ilike(f'%{query}%')).all()
        elif search_tag == 'reach':
            data = influencers.query.filter(influencers.reach.ilike(f'%{query}%')).all()
        else:
            data = []

        return rt('search_results_influencer.html', search_data=data, ongoing_campaigns=ongoing_campaigns)

    return rt('sponsor_dashboard.html', ongoing_campaigns=ongoing_campaigns, sponsor_id=sponsor_id)


@app.route('/sponsor_requests')
@auth_required
def sponsor_requests():
    sponsor_id = session.get('user_id')
    if not sponsor_id:
        flash('You must be logged in to view this page.', 'warning')
        return rd('/')
    
    # Fetch sent requests related to the sponsor
    sent_requests = db.session.query(adrequest, influencers).join(campaigns, adrequest.campaign_id == campaigns.campaign_id).join(influencers, adrequest.influencer_id == influencers.id).filter(campaigns.sponsor_id == sponsor_id, adrequest.direction == 'to_influencer').all()
    
    # Fetch received requests related to the sponsor
    received_requests = db.session.query(adrequest, influencers).join(campaigns, adrequest.campaign_id == campaigns.campaign_id).join(influencers, adrequest.influencer_id == influencers.id).filter(campaigns.sponsor_id == sponsor_id, adrequest.direction == 'to_sponsor').all()
    
    return rt('sponsor_requests.html', sent_requests=sent_requests, received_requests=received_requests)





@app.route('/send_ad_request', methods=['POST'])
@auth_required
def send_ad_request():
    # Get the form data
    campaign_name = rq.form.get('camp_name')
    
    influencer_id = rq.form.get('influencer_id')
    sponsor_id = session.get('user_id')

    # Get the corresponding campaign
    campaign = campaigns.query.filter_by(sponsor_id=sponsor_id, camp_name=campaign_name).first()

    if not campaign:
        flash('Campaign not found.', 'warning')
        return rd('/search_influencer')

    # Check if an ad request for this campaign and influencer already exists
    existing_request = adrequest.query.filter_by(campaign_id=campaign.campaign_id, influencer_id=influencer_id).first()
    if existing_request:
        flash('Ad request for this campaign and influencer already exists.', 'warning')
        return rd('/search_influencer')

    # Create a new ad request
    new_request = adrequest(
        campaign_id=campaign.campaign_id,
        campaign_name=campaign.camp_name,
        influencer_id=influencer_id,
        ads_required=campaign.ads_required, 
        payment_amount=campaign.budget,
        status='Pending',
        direction='to_influencer'
    )

    # Add the new request to the session and commit
    db.session.add(new_request)
    db.session.commit()

    flash('Ad request sent successfully!', 'success')
    return rd('/sponsor_dashboard')




@app.route('/edit_ad_request/<int:request_id>', methods=['GET', 'POST'])
@auth_required
def edit_ad_request(request_id):
    ad_request = adrequest.query.get_or_404(request_id)
    if rq.method == 'POST':
        ad_request.campaign_name = rq.form['campaign_name']
        ad_request.ads_required = rq.form['ads_required']
        ad_request.payment_amount = rq.form['payment_amount']
        db.session.commit()
        flash('Ad request updated successfully!', 'success')
        return redirect(url_for('sponsor_requests'))
    return rt('edit_ad_request.html', ad_request=ad_request)



@app.route('/delete_ad_request/<int:request_id>', methods=['POST'])
def delete_ad_request(request_id):
    ad_request = adrequest.query.get_or_404(request_id)
    db.session.delete(ad_request)
    db.session.commit()
    flash('Ad request deleted successfully!', 'success')
    return redirect(url_for('sponsor_requests'))


@app.route('/pay_ad_request/<int:request_id>', methods=['POST'])
def pay_ad_request(request_id):
    ad_request = adrequest.query.get(request_id)
    if not ad_request:
        flash('Request not found.', 'error')
        return redirect(url_for('sponsor_dashboard'))

    # Update the request status to Paid
    ad_request.status = 'Paid'
    db.session.commit()

    flash('Payment successful.', 'success')
    return redirect(url_for('sponsor_dashboard'))


@app.route('/sponsor_stats', methods = ['GET','POST'] )
def sponsor_stats():
    sponsor_id = session.get('user_id')
    return rt ('sponsor_stats.html')


@app.route('/get_sponsor_campaign_data', methods=['GET'])
def get_sponsor_campaign_data():
    sponsor_id = session.get('user_id')
    if not sponsor_id:
        return jsonify({'error': 'No sponsor ID found'}), 400
    # Get sponsor name
    sponsor = users.query.filter_by(id=sponsor_id, user_type='sponsor').first()
    
    sponsor_name = sponsor.username

    # Get campaign data
    created_campaigns_count = campaigns.query.filter_by(sponsor_id=sponsor_id).count()

    # Get accepted and paid campaign counts from adrequests
    accepted_campaigns_count = adrequest.query.join(campaigns).filter(
        campaigns.sponsor_id == sponsor_id,
        adrequest.status == 'Accepted'
    ).count()

    paid_campaigns_count = adrequest.query.join(campaigns).filter(
        campaigns.sponsor_id == sponsor_id,
        adrequest.status == 'Paid'
    ).count()

    data_dict = {
        "sponsor_name": sponsor_name,
        "campaign_data": [
            created_campaigns_count,
            accepted_campaigns_count,
            paid_campaigns_count
        ]
    }

    return jsonify(data_dict)




############################ influencer related routes ###################################


@app.route('/influencer_signup', methods = ['GET','POST'])

def influencer_signup():
    if rq.method == 'POST':
        email = rq.form['email']
            

        if not users.query.filter(users.email == email).all():
            newuser = users(username = rq.form['username'] , email = rq.form['email'], password = rq.form['password'] , user_type='influencer')
            db.session.add(newuser)
            db.session.commit()

            session['username'] = newuser.username

            new_influencer = influencers(id=newuser.id, name=rq.form['name'], reach=rq.form['reach'] , niche=rq.form['niche'])
            db.session.add(new_influencer)  # Add objects
            db.session.commit()
            flash('Influencer has been created successfully','success')
        return rd('/')

    return rt('influencer_signup.html')



@app.route('/influencer_dashboard')
@auth_required
def influencer_dashboard():
    if session.get('role') != 'influencer':
        flash('Unauthorized access.', 'danger')
        return rd(uf('home'))

    username = session.get('username')
    influencer_id = session.get('user_id')

    # Get ongoing campaigns (excluding public ones)
    ongoing_campaigns = adrequest.query.join(campaigns).filter(
        adrequest.influencer_id == influencer_id,
        adrequest.status == 'Accepted'
    ).all()

    # Combine ad requests with their corresponding campaigns and calculate progress
    ad_requests = adrequest.query.join(campaigns).filter(
        adrequest.influencer_id == influencer_id
    ).all()

    combined_requests = []
    for request in ad_requests:
        total_ads = request.campaign.ads_required
        completed_ads = request.ads_completed
        progress = (completed_ads / total_ads) * 100 if total_ads else 0
        combined_requests.append({
            'request': request,
            'campaign': request.campaign,
            'progress': progress
        })

    return rt('influencer_dashboard.html', username=username, ongoing_campaigns=ongoing_campaigns, ad_requests=combined_requests)




@app.route('/search_sponsor', methods=['POST'])
@auth_required
def search_sponsor():
    search_tag = rq.form.get('search_tag')
    search_query = rq.form.get('search_query')

    if not search_query:
        flash('Search query cannot be empty.', 'danger')
        return rd(uf('influencer_dashboard'))

    

    search_results = []
    if search_tag == 'camp_name':
        search_results = campaigns.query.filter(campaigns.camp_name.like('%'+search_query+'%'),campaigns.status != 'Flagged',campaigns.visibility == 'public').all()

    if search_tag == 'camp_category':
        search_results = campaigns.query.filter(campaigns.camp_category.like('%'+search_query+'%'),campaigns.status != 'Flagged',campaigns.visibility == 'public').all()

    if search_tag == 'budget':
        search_results = campaigns.query.filter(campaigns.budget.like('%'+search_query+'%'),campaigns.status != 'Flagged',campaigns.visibility == 'public').all()
    

    
    return rt('search_results_campaign.html', search_data=search_results)



@app.route('/update_ads_completed/<int:adrequest_id>', methods=['POST'])
@auth_required
def update_ads_completed(adrequest_id):
    ad_request = adrequest.query.get_or_404(adrequest_id)
    ads_completed = rq.form.get('ads_completed', type=int)
    ad_request.ads_completed = ads_completed
    db.session.commit()
    flash(' Updated successfully!','success')
    return rd(uf('influencer_dashboard'))




@app.route('/influencer_requests')
@auth_required
def influencer_requests():
    influencer_id = session.get('user_id')
    if not influencer_id:
        flash('You must be logged in to view this page.', 'warning')
        return rd('/')

    # Fetch received requests related to the influencer
    received_requests = db.session.query(
        adrequest.id,
        campaigns.camp_name,
        users.username.label('sponsor_name'),
        adrequest.ads_required,
        adrequest.payment_amount,
        adrequest.status
    ).join(
        campaigns, adrequest.campaign_id == campaigns.campaign_id
    ).join(
        users, campaigns.sponsor_id == users.id
    ).filter(
        adrequest.influencer_id == influencer_id,
        adrequest.direction == 'to_influencer'
    ).all()

    # Fetch sent requests related to the influencer
    sent_requests = db.session.query(
        adrequest.id,
        campaigns.camp_name,
        users.username.label('sponsor_name'),
        adrequest.ads_required,
        adrequest.payment_amount,
        adrequest.status
    ).join(
        campaigns, adrequest.campaign_id == campaigns.campaign_id
    ).join(
        users, campaigns.sponsor_id == users.id
    ).filter(
        adrequest.influencer_id == influencer_id,
        adrequest.direction == 'to_sponsor'
    ).all()

   
   

    return rt('influencer_requests.html', received_requests=received_requests, sent_requests=sent_requests)




@app.route('/respond_ad_request/<int:request_id>', methods=['POST'])
@auth_required
def respond_ad_request(request_id):
    action = rq.form.get('action')
    ad_request = adrequest.query.get_or_404(request_id)
    if action == 'accept':
        ad_request.status = 'Accepted'
    elif action == 'reject':
        ad_request.status = 'Rejected'
    db.session.commit()
    flash('Request updated successfully.', 'success')
    return rd(rq.referrer)





@app.route('/influencer_profile')
@auth_required
def influencer_profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('You must be logged in to view your profile.', 'warning')
        return rd(uf('home'))

    influencer = influencers.query.filter_by(id=user_id).first()
    user = users.query.filter_by(id=user_id).first()
    if not influencer:
        flash('Influencer profile not found.', 'error')
        return rd(uf('home'))

    return rt('influencer_profile.html', influencer=influencer, user = user)




@app.route('/update_profile', methods=['POST'])
def update_profile():
    influencer_id = session.get('user_id')
    user = users.query.get(influencer_id)
    influencer = influencers.query.get(influencer_id)

    user.username = rq.form['username']
    user.email = rq.form['email']
    influencer.niche = rq.form['niche']
    influencer.reach = rq.form['reach']

    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('influencer_profile'))




@app.route('/send_influencer_request/<int:campaign_id>', methods=['POST'])
@auth_required
def send_influencer_request(campaign_id):
    influencer_id = session.get('user_id')
    if not influencer_id:
        flash('You must be logged in to send a request.', 'warning')
        return redirect('/influencer_dashboard')

    campaign = campaigns.query.get(campaign_id)
    if not campaign:
        flash('Campaign not found.', 'danger')
        return redirect('/influencer_dashboard')

    # Create a new ad request
    new_request = adrequest(
        campaign_id=campaign.campaign_id,
        campaign_name=campaign.camp_name,
        influencer_id=influencer_id,
        ads_required = campaign.ads_required,
        payment_amount=campaign.budget,  
        status='Pending',
        direction='to_sponsor'
    )

    db.session.add(new_request)
    db.session.commit()
    flash('Request sent successfully.', 'success')
    return redirect('/influencer_dashboard')



@app.route('/influencer_stats', methods = ['GET','POST'])
@auth_required
def influencer_stats():
    return rt('influencer_stats.html')



@app.route('/get_influencer_requests_stats', methods=['GET'])
def get_influencer_requests_stats():
    influencer_id = session.get('user_id')
    if not influencer_id:
        return jsonify({'error': 'No influencer ID found'}), 400

    # Query requests sent by the influencer
    requests_sent_count = adrequest.query.filter(
        adrequest.influencer_id == influencer_id,
        adrequest.direction == 'to_sponsor'
    ).count()

    # Query requests received by the influencer
    requests_received_count = adrequest.query.filter(
        adrequest.influencer_id == influencer_id,
        adrequest.direction == 'to_influencer'
    ).count()

    data_dict = {
        'labels': ['Requests Sent', 'Requests Received'],
        'data': [requests_sent_count, requests_received_count]
    }

    return jsonify(data_dict)






# route to log out
@app.route('/logout')
@auth_required
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return rd(uf('home'))



if __name__ == '__main__':
    db.create_all()
    app.debug = True
    app.run(host='0.0.0.0')

