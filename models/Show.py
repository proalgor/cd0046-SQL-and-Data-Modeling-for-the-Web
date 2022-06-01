from sqlalchemy import DateTime
from helpers.connection import db

class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), nullable = False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable = False)
    start_time = db.Column(DateTime, nullable = False)