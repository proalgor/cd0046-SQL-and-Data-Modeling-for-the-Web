#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
from datetime import datetime
from re import A
from time import time
from unicodedata import name
from unittest import removeResult
from wsgiref.handlers import format_date_time
from flask import Flask, jsonify, render_template, request, Response, flash, redirect, session, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import Date, desc
from forms import *
from helpers.filters import format_datetime
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from helpers.connection import db
from models.Artist import Artist
from models.Venue import Venue
from models.Show import Show
from helpers.lib import get_entity_dict
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__, instance_relative_config=True)
moment = Moment(app)
app.config.from_object('config')
app.config.from_pyfile('config.py')

#Disabled csrf
#csrf = CSRFProtect(app)
db.init_app(app)

migrate = Migrate(app, db)
#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  recent_venues=db.session.query(Venue.id, Venue.name).order_by(desc(Venue.id)).limit(2)
  recent_artists=db.session.query(Artist.id, Artist.name).order_by(desc(Artist.id)).limit(2)
  return render_template('pages/home.html', venues=recent_venues, artists=recent_artists)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
  venues = db.session.query(Venue.id, Venue.name, Venue.state, Venue.city).all()
  time_now = datetime.now().isoformat()
  agg_venue = {}
  for venue in venues:
    if not agg_venue.get(venue.city):
      agg_venue[venue.city] = {
        'city': venue.city,
        'state': venue.state,
        'venues':[{
          'id': venue.id,
          'name': venue.name,
          'num_upcoming_shows': db.session.query(Show.id).join(Venue).filter(Show.venue_id == venue.id, Show.start_time > time_now).count()
        }]
      }
      continue
    agg_venue[venue.city]['venues'].append({
        'id': venue.id,
        'name': venue.name,
        'num_upcoming_shows': db.session.query(Show.id).join(Venue).filter(Show.venue_id == venue.id, Show.start_time > time_now).count()
    })
  return render_template('pages/venues.html', areas=agg_venue.values());

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_q=request.form.get('search_term', '')
  time_now = datetime.now().isoformat()
  venue = db.session.query(Venue.id, Venue.name).filter(Venue.name.ilike(f'%{search_q}%')).all()
  response = {
    "count":0,
    "data":[]
  }
  for venue in venues:
    response["count"] += 1
    response["data"].append({
      'id': venue.id,
      'name': venue.name,
      'num_upcoming_shows': db.session.query(Show.id).filter(Show.artist_id == venue.id, Show.start_time > time_now).count()
    })
  return render_template('pages/search_venues.html', results=response, search_term=search_q)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)
  if not venue:
    flash('The artist does not exist')
    return render_template('pages/home.html')
  #shows = venue.events
  past_shows = db.session.query(Artist.id.label('artist_id'), Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link'), Show.start_time.label('start_time')).join(Show).filter(Show.venue_id == venue_id).filter(Show.start_time < datetime.now()).all()
  upcoming_shows = db.session.query(Artist.id.label('artist_id'), Artist.name.label('artist_name'), Artist.image_link.label('artist_image_link'), Show.start_time.label('start_time')).join(Show).filter(Show.venue_id == venue_id).filter(Show.start_time > datetime.now()).all()
  # for show in shows:
  #   values = {
  #     'artist_id': show.artist.id,
  #     'artist_name': show.artist.name,
  #     'artist_image_link': show.artist.image_link,
  #     'start_time': show.start_time.isoformat()
  #   }
  #   if show.start_time.isoformat() < datetime.now().isoformat():
  #     past_shows.append(values)
  #     continue
  #   upcoming_shows.append(values) 
  venue = get_entity_dict(venue)
  venue['genres'] = venue['genres'].split(',')
  venue['upcoming_shows'] = upcoming_shows
  venue['past_shows'] = past_shows
  venue['upcoming_shows_count'] = len(upcoming_shows)
  venue['past_shows_count'] = len(past_shows)
  
  return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm()
  error = False
  try:
    if form.validate_on_submit():
      # convert the genre to string
      genreString = ','.join(str(x) for x in form.data['genres'])
      venue = Venue(
        name = form.data['name'],
        city = form.data['city'],
        state = form.data['state'], 
        address= form.data['address'], 
        phone = form.data['phone'],
        image_link = form.data['image_link'],
        genres = genreString,
        facebook_link = form.data['facebook_link'],
        website_link= form.data['website_link'],
        seeking_talent = form.data['seeking_talent'],
        seeking_description = form.data['seeking_description'],
      )
      db.session.add(venue)
      db.session.commit()
    else:
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed. error = '+ str(form.errors))
      return render_template('forms/new_venue.html', form = form)
  except:
    db.session.rollback() 
    error = True
  finally:
    db.session.close()
  if  error == True:
    flash('Internal error' + request.form['name'] + 'could not be listed ')
    return render_template('pages/home.html')

  # Return success if there is no error
  flash('Venue ' + request.form['name'] + ' was successfully listed!')
  return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  venue = Venue.query.get(venue_id)
  error = False
  if not venue:
    flash('The venue does not exist')
    return render_template('pages/home.html')
  try:
    db.session.delete(venue)
    db.session.commit()
  except:
    error = True
    db.rollback()
  finally:
    db.close()
  if error:
    abort(500)
  return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = db.session.query(Artist.id, Artist.name).all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_q=request.form.get('search_term', '')
  time_now = datetime.now().isoformat()
  artists = db.session.query(Artist.id, Artist.name).filter(Artist.name.ilike(f'%{search_q}%')).all()
  response = {
    "count":0,
    "data":[]
  }
  for artist in artists:
    response["count"] += 1
    response["data"].append({
      'id': artist.id,
      'name': artist.name,
      'num_upcoming_shows': db.session.query(Show.id).filter(Show.artist_id == artist.id, Show.start_time > time_now).count()
    })
  return render_template('pages/search_artists.html', results=response, search_term=search_q)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = Artist.query.get(artist_id)
  if not artist:
    flash('The artist does not exist')
    return render_template('pages/home.html')
  # shows = artist.events
  past_shows = db.session.query(Venue.id.label('venue_id'), Venue.name.label('venue_name'), Venue.image_link.label('venue_image_link'), Show.start_time.label('start_time')).join(Show).filter(Show.artist_id == artist_id).filter(Show.start_time< datetime.now()).all()
  upcoming_shows = db.session.query(Venue.id.label('venue_id'), Venue.name.label('venue_name'), Venue.image_link.label('venue_image_link'), Show.start_time.label('start_time')).join(Show).filter(Show.artist_id == artist_id).filter(Show.start_time > datetime.now()).all()
  # for show in shows:
  #   values = {
  #     'venue_id': show.venue.id,
  #     'venue_name': show.venue.name,
  #     'venue_image_link': show.venue.image_link,
  #     'start_time': show.start_time.isoformat()
  #   }
  #   if show.start_time.isoformat() < datetime.now().isoformat():
  #     past_shows.append(values)
  #     continue
  #   upcoming_shows.append(values) 
  artist = get_entity_dict(artist)
  artist['genres'] = artist['genres'].split(',')
  artist['upcoming_shows'] = upcoming_shows
  artist['past_shows'] = past_shows
  artist['upcoming_shows_count'] = len(upcoming_shows)
  artist['past_shows_count'] = len(past_shows)
  
  return render_template('pages/show_artist.html', artist=artist)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  if not artist:
    flash('Artist with id '+ str(artist_id) + ' does not exist')
    return render_template('pages/home.html')
  # get the dictionary rep of the venue obj
  artistDict = get_entity_dict(artist)
  #set the genres back to array
  artistDict['genres'] = artistDict["genres"].split(',')
  form = ArtistForm(data = artistDict)

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # artist record with ID <artist_id> using the new attributes
  form = ArtistForm()
  if form.validate_on_submit():
    genreString = ','.join(str(x) for x in form.data['genres'])
    artist = Artist.query.get(artist_id)
    form.populate_obj(artist)
    # set the genre back to string
    artist.genres = genreString
    db.session.commit()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  # get the dictionary rep of the venue obj
  venueDictionary = get_entity_dict(venue)
  #set the genres back to array
  venueDictionary['genres'] = venueDictionary["genres"].split(',')
  form = VenueForm(data = venueDictionary)
  
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # venue record with ID <venue_id> using the new attributes
  form = VenueForm()
  if form.validate_on_submit():
    genreString = ','.join(str(x) for x in form.data['genres'])
    venue = Venue.query.get(venue_id)
    form.populate_obj(venue)
    # set the genre back to string
    venue.genres = genreString
    db.session.commit()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm()
  error = False
  try:
    if form.validate_on_submit():
      # convert the genre to string
      genreString = ','.join(str(x) for x in form.data['genres'])
      artist = Artist(
        name = form.data['name'],
        city = form.data['city'],
        state = form.data['state'], 
        phone = form.data['phone'],
        image_link = form.data['image_link'],
        genres = genreString,
        facebook_link = form.data['facebook_link'],
        website_link= form.data['website_link'],
        seeking_venue = form.data['seeking_venue'],
        seeking_description = form.data['seeking_description'],
      )
      db.session.add(artist)
      db.session.commit()
    else:
      flash('An error occurred. Artist' + request.form['name'] + ' could not be listed. error = '+ str(form.errors))
      return render_template('forms/new_artist.html', form = form)
  except Exception as e:
    db.session.rollback() 
    error = True
  finally:
    db.session.close()
  if  error == True:
    flash('Internal error' + request.form['name'] + 'could not be listed ')
    return render_template('pages/home.html')

  # Return success if there is no error
  flash('Artist ' + request.form['name'] + ' was successfully listed!')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows.
  data = Show.query.all()
  returnData = []
  for d in data:
    values = {
      'venue_id': d.venue.id,
      'venue_name': d.venue.name,
      'artist_id': d.artist.id,
      'artist_name': d.artist.name,
      'artist_image_link': d.artist.image_link,
      'start_time': d.start_time.isoformat()
    }
    returnData.append(values)
  return render_template('pages/shows.html', shows=returnData)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  form = ShowForm()
  if form.validate_on_submit():
    artistExists = db.session.query(db.exists().where(Artist.id == form.data['artist_id'])).scalar()
    venueExists = db.session.query(db.exists().where(Venue.id == form.data['venue_id'])).scalar()
    if not artistExists or not venueExists:
      flash('The venue or artist does not exit')
      return render_template('forms/new_show.html', form=form)
    show = Show(
      artist_id = form.data['artist_id'],
      venue_id = form.data['venue_id'],
      start_time = form.data['start_time']
    )
    db.session.add(show)
    db.session.commit()
  else:
    flash('Please insert the correct values')
    return render_template('forms/new_show.html', form=form)
  # on successful db insert, flash success
  flash('Show was successfully listed!')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
