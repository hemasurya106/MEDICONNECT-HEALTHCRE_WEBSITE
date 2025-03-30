from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from datetime import datetime
import os
from together import Together
from sqlalchemy import or_

# --------------------------- Importing Tables ---------------------------

from Tables import Patients, Doctors, Appointments, db, app

#------------------------------------ API ------------------------------------------------------

os.environ["TOGETHER_API_KEY"] = "1f2f813f249d37423c14343daacdd9a1dae6f387b37e9e89e5c0bad4d15b585b"

# Add this check before creating the Together client
if not os.environ.get("TOGETHER_API_KEY"):
    raise ValueError("Missing TOGETHER_API_KEY environment variable")
client = Together()

#------------------------------------ Chat Bot ------------------------------------------------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    try:
        user_message = request.json.get("message", "")
        
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B-free",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=300,  # Increased to allow complete responses
            temperature=0.7
        )

        # Clean the response
        raw_response = response.choices[0].message.content
        clean_response = raw_response.replace("<think>", "").replace("</think>", "").strip()
        
        # Remove any incomplete sentences at the end
        if clean_response and clean_response[-1] not in {'.', '!', '?'}:
            clean_response = clean_response.rsplit('.', 1)[0] + '.'

        return jsonify({"reply": clean_response})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

#------------------------------------ Functions ------------------------------------------------------

def Login_Verification(data):
    user_record = Patients.query.filter_by(email = data['email']).first()

    if user_record:
        password_check = user_record.password == data['password']

        if password_check:
            session['patient_id'] = user_record.p_id
            session['patient_name'] = user_record.f_name
            return True
        else:
            return False
    
    else:
        return False
    
def Add_Patient(data):
    dup_email = Patients.query.filter_by(email = data['email']).first()

    if dup_email or (data['password'] != data['confirm_password']):
        return False
    
    else:
        new_patient = Patients(
            f_name=data['first_name'],
            l_name=data['last_name'],
            email=data['email'],
            password=data['password'],
            dob=data.get('dob', None),
            gender=data.get('gender', None),
            allergies=data.get('allergies', None),
            ch_conditions=data.get('ch_conditions', None),
            surgeries=data.get('surgeries', None),
            medications=data.get('medications', None),
            em_name=data.get('em_name', None),
            em_rel=data.get('em_rel', None),
            em_phone=data.get('em_phone', None),
        )
        
        db.session.add(new_patient)
        db.session.commit()

        user_record = Patients.query.filter_by(email = data['email']).first()

        session['patient_id'] = user_record.p_id
        session['patient_name'] = user_record.f_name

        return True

def Patient_Details(patient_id):
    record = Patients.query.filter_by(p_id = patient_id).first()

    if record:
        return {
            'first_name': record.f_name,
            'last_name': record.l_name,
            'email': record.email,
            'address': record.address,
            'ph_number': record.ph_number,
            'dob': record.dob,
            'gender': record.gender,
            'allergies': record.allergies,
            'ch_conditions': record.ch_conditions,
            'surgeries': record.surgeries,
            'medications': record.medications,
            'em_name': record.em_name,
            'em_rel': record.em_rel,
            'em_phone': record.em_phone
        }
    else:
        return None

def Add_Appointment(data):
    try:
        patient_id = session.get('patient_id')
        doctor = Doctors.query.filter_by(d_id = data['d_id']).first()
        
        appointment_date = datetime.strptime(data['date'], "%Y-%m-%d").date()

        new_appointment = Appointments(
            p_id = patient_id,
            d_id = doctor.d_id,
            date = appointment_date,
            comments = data['info']
        )

        db.session.add(new_appointment)
        db.session.commit()

        return True
    
    except:
        return False

def Edit_Patient_Profile(data):
    patient_id = session.get('patient_id')

    patient_data = Patients.query.filter_by(p_id = patient_id).first()

    if patient_data:
        patient_data.ph_number = data['ph_number']
        patient_data.address = data['address']
        patient_data.em_name = data['em_name']
        patient_data.em_phone = int(data['em_phone'])
        patient_data.em_rel = data['em_rel']

        db.session.commit()
        return True

    else:
        return False
    
@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    # Get the patient ID from the request (this could be from session or query parameter)
    patient_id = session.get('patient_id')

    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    # Query appointments for the patient, joining with the Doctors table
    appointments = db.session.query(Appointments, Doctors.name, Doctors.speciality).\
        join(Doctors, Appointments.d_id == Doctors.d_id).\
        filter(Appointments.p_id == patient_id).all()

    if not appointments:
        return jsonify({"message": "No appointments found for this patient"}), 404

    # Prepare the response data
    appointments_data = []
    for appointment, doctor_name, doctor_speciality in appointments:
        appointments_data.append({
            'appointment_id': appointment.a_id,
            'doctor_name': doctor_name,
            'doctor_speciality': doctor_speciality,
            'date': appointment.date.strftime('%b %d, %Y'),
            'comments': appointment.comments
        })

    return jsonify(appointments_data)

@app.route('/api/appointments/<int:id>', methods=['DELETE'])
def delete_appointment(id):
    print("Hello")
    appointment = Appointments.query.filter_by(a_id = id).first()
    if appointment:
        db.session.delete(appointment)
        db.session.commit()
        return '', 204
    return 'Appointment not found', 404

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    try:
        # Get search parameters from query string
        name = request.args.get('name', '').lower()
        speciality = request.args.get('speciality', '')
        location = request.args.get('location', '').lower()

        # Base query
        query = Doctors.query

        # Apply filters if parameters are provided
        if name:
            query = query.filter(Doctors.name.ilike(f'%{name}%'))
        if speciality:
            query = query.filter(Doctors.speciality == speciality)
        if location:
            query = query.filter(or_(
                Doctors.address.ilike(f'%{location}%'),
                # Add other location-related fields if needed
            ))

        doctors = query.all()

        if not doctors:
            return jsonify({'error': 'No doctors found matching your criteria'}), 404

        doctors_data = []
        for doctor in doctors:
            doctors_data.append({
                'd_id': doctor.d_id,
                'name': doctor.name,
                'speciality': doctor.speciality,
                'address': doctor.address,
                'experience': f"{doctor.experience} years"
            })

        return jsonify(doctors_data)

    except Exception as e:
        app.logger.error(f"Error fetching doctors: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

#------------------------------------ Home Page ------------------------------------------------------

@app.route('/', methods=["GET"])
def Home():
    if request.method == "GET":
        return render_template("index.html")
    
    else:
        return render_template("error.html")

    
#------------------------------------ About Page ------------------------------------------------------
    
@app.route('/About', methods = ["GET"])
def About():
    if request.method == "GET":
        return render_template("about.html")
    
    else:
        return render_template("error.html")
    
#------------------------------------ Departments Page ------------------------------------------------------
    
@app.route('/Departments', methods = ["GET"])
def Departments():
    if request.method == "GET":
        return render_template("departments.html")
    
    else:
        return render_template("error.html")
    
#------------------------------------ Contact Us Page ------------------------------------------------------
    
@app.route('/Contact_Us', methods = ["GET"])
def Contact_Us():
    if request.method == "GET":
        return render_template("contact.html")
    
    elif request.method == "POST":
        return render_template("error.html")    # change later?
    
    else:
        return render_template("error.html")
    
#------------------------------------ Login Page ------------------------------------------------------

@app.route('/Login', methods = ["GET", "POST"])
def Login():
    if request.method == "GET":
        return render_template("login.html")
    
    elif request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        print(email, password)  #Just for debugging...

        data = {'email': email,
                'password': password}

        
        status = Login_Verification(data)
        if status == 1:
            data = {'first_name': session.get('patient_name')}
            return render_template("dashboard.html", data = data)
        
        elif status == 0:
            return render_template("login.html", error_msg = "The Username or email is Wrong!")
        
        else:
            return render_template("error.html")

    else:
        return render_template("error.html")

#------------------------------------ Sign Up Page ------------------------------------------------------

@app.route('/Sign_Up', methods = ["GET", "POST"])
def Sign_Up():
    if request.method == "GET":
        return render_template("sign_up.html")
    
    elif request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        print(first_name, last_name, email, password, confirm_password) #Just for debugging

        data = {'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password': password,
                'confirm_password': confirm_password}

        status = Add_Patient(data)
        
        if status == 1:
            data = {'first_name': session.get('patient_name')}
            return render_template("dashboard.html", data = data)
        
        elif status == 0:
            return render_template("sign_up.html", error_msg = "The email address is already registered!")
        
        else:
            return render_template("error.html")
    
    else:
        return render_template("error.html")

#------------------------------------ Dashboard Page ------------------------------------------------------
    
@app.route('/Dashboard', methods = ["GET", "POST"])
def Dashboard():
    if request.method == "GET":
        data = {'first_name': session.get('patient_name')}
        return render_template("dashboard.html", data = data)
    
    elif request.method == "POST":
        return render_template("error.html")
    
    else:
        return render_template("error.html")

#------------------------------------ Patient Appointments Page ------------------------------------------------------

@app.route('/Patient_Appointments', methods = ["GET"])
def Patient_Appointments():
    if request.method == "GET":

        #Create an API with and endpoint that gives output as Upcoming and Past Appointments (Need to change js in front end)

        data = {'first_name': session.get('patient_name')}
        return render_template("appointments.html", data = data)
    
    else:
        return render_template("error.html")
    
#------------------------------------ Book Appointment Page ------------------------------------------------------

@app.route('/Book_Appointment/', methods = ["GET", "POST"])
def Book_Appointment():
    if request.method == "GET":
        data = {'first_name': session.get('patient_name')}
        doctors = db.session.query(Doctors.d_id, Doctors.name).all()
        return render_template("app.html", data = data, doctors = doctors)
    
    elif request.method == "POST":
        
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        ph_number = request.form.get('phone')
        d_id = request.form.get('doctor')
        date = request.form.get('date')
        time = request.form.get('time')
        info = request.form.get('info')

        print(first_name, last_name, email, ph_number, d_id, date, time, info) # debugging

        data = {
                'f_name': first_name,
                'last_name': last_name,
                'email': email,
                'ph_number': ph_number,
                'd_id': d_id,
                'date': date,
                'time': time,
                'info': info
            }

        status = Add_Appointment(data)

        if status:
            data = {'first_name': session.get('patient_name')}
            doctors = db.session.query(Doctors.d_id, Doctors.name).all()
            return render_template("app.html", data = data, doctors = doctors)
        
        else:
            return render_template("error.html")
    
    else:
        return render_template("error.html")

#------------------------------------ Search Doctor Page ------------------------------------------------------

@app.route('/Search_Doctor', methods = ["GET", "POST"])
def Search_Doctor():
    if request.method == "GET":
        data = {'first_name': session.get('patient_name')}
        return render_template("search_doctor.html", data = data)
    
    elif request.method == "POST":
        return render_template("error.html")
    
    else:
        return render_template("error.html")
    
#------------------------------------ Profile Page ------------------------------------------------------

@app.route('/Profile', methods = ["GET", "POST"])
def Profile():
    if request.method == "GET":

        patient_id = session.get('patient_id')
        data = Patient_Details(patient_id)

        return render_template("profile.html", data = data)
    
    elif request.method == "POST":
        return redirect(url_for('Edit_Profile'))
    
    else:
        return render_template("error.html")
    
#------------------------------------ Edit Profile Page ------------------------------------------------------

@app.route('/Edit_Profile', methods = ["GET", "POST"])
def Edit_Profile():
    if request.method == "GET":

        patient_id = session.get('patient_id')
        data = Patient_Details(patient_id)
        
       
        return render_template("edit_profile.html", data = data)
    
    elif request.method == "POST":

        ph_number = request.form.get('ph_number')
        address = request.form.get('address')
        em_name = request.form.get('em_name')
        em_phone = request.form.get('em_phone')
        em_rel = request.form.get('em_rel')
        data = {'ph_number': ph_number,
                'address': address,
                'em_name': em_name,
                'em_phone': em_phone,
                'em_rel': em_rel
            }
        
        
        
        status = Edit_Patient_Profile(data)
        
        if status:
            return redirect(url_for('Profile'))
        
        else:
            return render_template("error.html")
    
    else:
        return render_template("error.html")

#------------------------------------ Logout Page ------------------------------------------------------

@app.route('/Logout', methods = ["GET"])
def Logout():
    if request.method == "GET":

        session.clear()

        return redirect(url_for('Home'))
    
    else:
        return render_template("error.html")
    
#------------------------------------ Run The Program ------------------------------------------------------

if __name__ == '__main__':
    app.run(debug = True, port = 8080)