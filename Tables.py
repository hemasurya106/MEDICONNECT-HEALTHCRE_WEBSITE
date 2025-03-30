from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'the_secret_key'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "Hospital_DB.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)
app.app_context().push()

# Define your models
class Patients(db.Model):
    __tablename__ = 'Patients'

    p_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    f_name = db.Column(db.String, nullable=False)
    l_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    address = db.Column(db.Text)
    ph_number = db.Column(db.Text)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String)
    allergies = db.Column(db.Text)
    ch_conditions = db.Column(db.Text)
    surgeries = db.Column(db.Text)
    medications = db.Column(db.Text)
    em_name = db.Column(db.String, nullable=False)
    em_rel = db.Column(db.String, nullable=False)
    em_phone = db.Column(db.String, nullable=False)

    # Relationship with appointments
    appointments = db.relationship("Appointments", back_populates="patient")

class Doctors(db.Model):
    __tablename__ = 'Doctors'

    d_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    speciality = db.Column(db.String, nullable=False)
    address = db.Column(db.Text)
    experience = db.Column(db.Integer, nullable=False)

    # Relationship with appointments
    appointments = db.relationship("Appointments", back_populates="doctor")

class Appointments(db.Model):
    __tablename__ = 'Appointments'

    a_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    p_id = db.Column(db.Integer, db.ForeignKey('Patients.p_id'), nullable=False)
    d_id = db.Column(db.Integer, db.ForeignKey('Doctors.d_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    comments = db.Column(db.Text)

    # Corrected relationships with Patients and Doctors
    patient = db.relationship("Patients", back_populates="appointments")
    doctor = db.relationship("Doctors", back_populates="appointments")


