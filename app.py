from datetime import datetime, timedelta
from enum import unique
from typing import final
from wsgiref.util import request_uri
from flask_bcrypt import Bcrypt
#from crypt import methods
from flask import Flask, session,render_template,  send_from_directory, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
import os,time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'e1d2604dab224c4ab9d6a4a558e7526e'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assignment3.db'
# extend session for 15 minutes 
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes = 15)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)



class Account(db.Model):
    __tablename__ = "Account"
    username = db.Column(db.String(20), unique=True, nullable = False,primary_key = True)
    name = db.Column(db.String(50), unique=True, nullable = False)
    email = db.Column(db.String(100), unique = True, nullable=False)
    password = db.Column(db.String(20), nullable = False)
    accountType = db.Column(db.String(20), nullable =False)
    
    
    def __repr__(self):
        return f"Account('{self.name}','{self.email}')"


#note that the attributes instructor and student are dangerous
#they might point to account that is different as required
#so check each time when you need to update or use this table
class Courses(db.Model):
    __tablename__ = "Courses"
    __table_args__ = (
        db.UniqueConstraint('student', 'exam_type','course_id', name = "unique_exam"),
        )
    id = db.Column(db.Integer, primary_key = True)
    course_id = db.Column(db.String(20), nullable = False)
    instructor = db.Column(db.String(20), db.ForeignKey('Account.username'), nullable = False)
    student = db.Column(db.String(20), db.ForeignKey('Account.username'))
    exam_type = db.Column(db.String(20), nullable = False)
    grades = db.Column(db.Float, nullable = False)
    time = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)


    def __repr__(self):
        return f"Courses('{self.id}','{self.student}','{self.grades}')"

    
class Feedback(db.Model):
    __tablename__ = "Feedback"
    id = db.Column(db.Integer, primary_key = True)
    course_id = db.Column(db.Integer)
    time = db.Column(db.DateTime, nullable = False,default = datetime.utcnow)
    q1 = db.Column(db.Text,default = "NA")
    q2 = db.Column(db.Text,default = "NA")
    q3 = db.Column(db.Text,default = "NA")
    q4 = db.Column(db.Text,default = "NA")
    instructor = db.Column(db.String(20), db.ForeignKey('Account.username'),  nullable = False)
    
class Regrade(db.Model):
    __tablename__ = "Regrade"
    id = db.Column(db.Integer, primary_key = True)
    time = db.Column(db.DateTime, nullable = False,default = datetime.utcnow)
    student = db.Column(db.String(20), db.ForeignKey('Account.username'), nullable = False)
    reason = db.Column(db.Text,default = "NA")
    instructor = db.Column(db.String(20), db.ForeignKey('Account.username'), nullable = False)
    course_id = db.Column(db.String(20),db.ForeignKey('Courses.course_id'),nullable = False)



@app.route("/")
def get_home():
    if not "name" in session:
        return redirect(url_for("login"))
    flash(f"Welcome {session.get('usertype')} {session.get('char_name')} to the home page of CSCB20!", "msg")
    return render_template("index.html",result_str = session.get("name"), usertype = session.get("usertype"))

@app.route("/calendar")
def get_calendar():
    if not "name" in session:
        return redirect(url_for("login"))
    return render_template("calendar.html")

@app.route("/lectures")
def get_lectures():
    if not "name" in session:
        return redirect(url_for("login"))
    return render_template("lectures.html")

@app.route("/resources")
def get_resources():
    if not "name" in session:
        return redirect(url_for("login"))
    return render_template("resources.html")

@app.route("/tutorials")
def get_tutorials():
    if not "name" in session:
        return redirect(url_for("login"))
    return render_template("tutorials.html")

@app.route("/administration",methods = ["GET","POST"])
def admin():
    if not "name" in session:
        return redirect(url_for("login"))
    usertype = session.get("usertype")
    if usertype == "instructor":
        if request.method == "GET":
            courses = db.session.query(Courses, Account).filter(Courses.instructor == session.get("name"))\
                .filter(Account.username == Courses.student)\
                    .filter(Account.accountType == "student").filter(Courses.exam_type == "enrollment").all()
            
            grade_result = []
            for i in courses:
                grade_result.append(
                    (
                        i[Courses].course_id,
                        i[Account].name,
                    )
                )
            return render_template("administration.html", grade_result = grade_result)
        else:
            courses = db.session.query(Courses, Account).filter(Courses.instructor == session.get("name"))\
                .filter(Account.username == Courses.student)\
                    .filter(Account.accountType == "student").filter(Courses.exam_type == "enrollment").all()
            
            grade_result = []
            for i in courses:
                grade_result.append(
                    (
                        i[Courses].course_id,
                        i[Account].name,
                    )
                )
            student = request.form["student"]
            course_id = request.form["course_id"]
            exam_type = "enrollment"
            new_mark = 1
            stu = db.session.query(Account).filter(Account.username == student).first()
            if not stu:
                flash("This student doesn't exist!","error")
                return render_template("administration.html", grade_result = grade_result)
            else:
                
                courses  = db.session.query(Courses, Account).filter(
                    Courses.course_id == course_id,
                    Courses.student == student,
                    Courses.exam_type == exam_type
                ).first()
                if not courses:
                    flash(f"{student} has been added to {course_id}","success")
                    add_course((course_id,session.get("name"),student, exam_type,new_mark))
                else:
                    flash("This student have already enrolled in the course","error")
                courses = db.session.query(Courses, Account).filter(Courses.instructor == session.get("name"))\
                    .filter(Account.username == Courses.student)\
                        .filter(Account.accountType == "student").filter(Courses.exam_type == "enrollment").all()
                
                grade_result = []
                for i in courses:
                    grade_result.append(
                        (
                            i[Courses].course_id,
                            i[Account].name,
                        )
                    )
                return render_template("administration.html", grade_result = grade_result)
        
    else:
        flash("You have no access to this page", "error")
        return redirect(url_for("login"))

@app.route("/feedback",methods=["GET", "POST"])
def get_feedback():
    # check if user is login
    if not "name" in session:
        return redirect(url_for("login"))
    
    usertype = session.get("usertype")
    if usertype == "student":
        if request.method == "POST":
            instructor = request.form["instructor"]
            course_id = request.form["course_id"]
            q1 = request.form["q1"]
            q2 = request.form["q2"]
            q3 = request.form["q3"]
            q4 = request.form["q4"]
            info = (q1,q2,q3,q4,instructor,course_id)
            # check if the instructor is in database
            target = Courses.query.filter_by(instructor = instructor, course_id = course_id,student=session.get("name")).first()
            if not target:
                flash("You are not eligible to write feedback to this course or instructor, try again!","error")
                return render_template("feedback.html",usertype = usertype)
            else:
                add_feedback(info)
                flash(f"Your feedback to {instructor} has been successfully submitted!", "msg")
                return render_template("feedback.html",usertype = usertype,username = session.get("name"))
        return render_template("feedback.html",usertype = usertype)
    else:
        feedbacks = db.session.query(Feedback).filter(Feedback.instructor == session.get("name"))
        return render_template("feedback.html", feedbacks = feedbacks, usertype = usertype)


@app.route("/regrade",methods=["GET", "POST"])
def regrade():
    if not "name" in session:
        return redirect(url_for("login"))
    usertype= session.get("usertype")
    if usertype == "student":
        courses_info = db.session.query(Courses, Account).filter(Courses.student == session.get("name"), Courses.exam_type == "enrollment")\
            .filter(Account.username == Courses.instructor).all()
        info_result = []
        for i in courses_info:
            info_result.append((
                i[Courses].course_id,
                i[Account].username,
                i[Account].name
            ))

        print(len(info_result))
        if request.method == "POST":
            instructor = request.form["instructor"]
            reason = request.form["reason"]
            course_id = request.form["course_id"]
            # check if the instructor is in database
            target = Courses.query.filter_by(instructor = instructor, course_id = course_id, student = session.get("name")).first()

            if not target:
                flash("This instructor or course is not found, try again!","error")
            elif Regrade.query.filter_by(instructor = instructor, course_id = course_id, student = session.get("name")).first():
                flash("You have a similar requst that is under under processing","msg")
            else:
                info = (session.get("name"),reason,instructor,course_id)
                add_regrade(info)
                flash(f"Your regrade request to {instructor} regarding {course_id} has been successfully submitted!", "success")
            
        return render_template("regrade.html",usertype = usertype, username = session.get("name"), courses_info = info_result)
    else:
        regrade_requests = db.session.query(Regrade, Account).filter(Regrade.instructor == session.get("name"))\
            .filter(Account.username == Regrade.student).all()

        request_result = []
        for i in regrade_requests:
            request_result.append(
                (i[Regrade].course_id,
                i[Account].username,
                i[Account].name,
                i[Regrade].reason)
            )
        return render_template("regrade.html", regrade_requests = request_result, usertype = usertype)

@app.route("/grades", methods = ["GET", "POST"])
def grades():
    if not "name" in session:
        return redirect(url_for("login"))
    usertype= session.get("usertype")
    if usertype == "student":
        courses = db.session.query(Courses, Account).filter(Courses.student == session.get("name"), Courses.exam_type!="enrollment")\
            .filter(Account.username == Courses.instructor)\
                .filter(Account.accountType == "instructor").all()

        grade_result = []
        for i in courses:
            grade_result.append(
                (
                    i[Courses].course_id,
                    i[Account].name,
                    i[Courses].exam_type,
                    i[Courses].grades
                )
            )
        return render_template("grades.html",usertype = usertype, grade_result = grade_result)
    #if the user is instructor
    else:
        #Printed all students's grade
        courses = db.session.query(Courses, Account).filter(Courses.instructor == session.get("name"), Courses.exam_type!="enrollment")\
                .filter(Account.username == Courses.student)\
                    .filter(Account.accountType == "student").all()    
        grade_result = []
        for i in courses:
            grade_result.append(
                (
                    i[Courses].course_id,
                    i[Account].username,
                    i[Account].name,
                    i[Courses].exam_type,
                    i[Courses].grades
                )
            )
        if request.method == "GET":
            return render_template("grades.html",usertype = usertype,grade_result = grade_result)
        #if the instructor want to change some marks
        else:
            student = request.form["student"]
            course_id = request.form["course_id"]
            exam_type = request.form["exam_type"]
            new_mark = request.form["new_mark"]
            courses  = db.session.query(Courses, Account).filter(
                Courses.instructor == session.get("name"),
                Courses.course_id == course_id,
                Courses.student == student,
                Courses.exam_type == "enrollment"
            ).filter(Account.username == Courses.student)\
                .filter(Account.accountType == "student").all()
            # you cannot enroll student from here
            # if the student has not marks result in this course
            if not courses or exam_type == "enrollment":
                flash("Please ensure all the information has been entered correctly !", "error")
                return render_template("grades.html",usertype = usertype,grade_result = grade_result)
            else:
                courses  = db.session.query(Courses).filter(
                    Courses.instructor == session.get("name"), 
                    Courses.course_id == course_id,
                    Courses.student == student,
                    Courses.exam_type == exam_type
                ).first()
                if courses:
                    flash(f"{student}'s {exam_type} is now {new_mark}","success")
                    db.session.delete(db.session.query(Courses).filter(
                        Courses.instructor == session.get("name"), 
                        Courses.course_id == course_id,
                        Courses.student == student,
                        Courses.exam_type == exam_type
                    ).first())
                    regrade_request = db.session.query(Regrade).filter(
                    Regrade.instructor == session.get("name"), 
                    Regrade.course_id == course_id,
                    Regrade.student == student,
                    ).first()
                    if regrade_request:
                        db.session.delete(regrade_request)
                    db.session.commit()
                add_course((course_id, session.get("name"), student, exam_type, float(new_mark)))
                db.session.commit()

                courses = db.session.query(Courses, Account).filter(Courses.instructor == session.get("name"), Courses.exam_type!="enrollment")\
                .filter(Account.username == Courses.student)\
                    .filter(Account.accountType == "student").all()
                grade_result = []
                for i in courses:
                    grade_result.append(
                        (
                            i[Courses].course_id,
                            i[Account].username,
                            i[Account].name,
                            i[Courses].exam_type,
                            i[Courses].grades
                        )
                    )

            return render_template("grades.html",usertype = usertype,grade_result = grade_result)

@app.route("/download/syllabus")
def get_syllabus():
    if not "name" in session:
        return redirect(url_for("login"))
    dir = os.path.abspath(os.getcwd())
    filePath = dir + '/static/files'
    return send_from_directory(filePath, 'fake.pdf')

@app.route("/assignment")
def get_assignment():
    if not "name" in session:
        return redirect(url_for("login"))
    return render_template("assignment.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # logout first
    if request.method == "GET":
        logout()
        return render_template("register.html")
    
    elif request.form["password"] != request.form["checkpassword"]:
        flash("The password was not the same, please check again")
        return render_template("register.html")
    else:
        username = request.form["username"]
        name = request.form["name"]
        email = request.form["email"]
        account = Account.query.filter_by(username = username).first()

        if(account):
            flash("Username already exist, Please try something else","error")
            return render_template("register.html")
        elif(Account.query.filter_by(email = email).first()):
            flash("Email alreadyt exist, Please try another one","error")
            return render_template("register.html")
        else:
            register_type = request.form.get("register type")
            hashed_password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
            info = (username, name, email, hashed_password, register_type)
            add_account(info)
            time.sleep(0.5)
            flash("Registration Successful, redirecting to login page","success")
            return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "name" in session:
            flash('already logged in!!',"success")
            return redirect(url_for('get_home'))
        else:
            return render_template("login.html")
    else:
        username = request.form["username"]
        password = request.form["password"]
        register_type = request.form.get("register type")
        
        account = Account.query.filter_by(username = username, accountType = register_type).first()
        if not account or not bcrypt.check_password_hash(account.password,password):
                flash("Please check your login details and try again","error")
                return render_template("login.html")
        else:
            session["name"] = username
            session["char_name"] = account.name
            session.permanent = True
            session["usertype"] = register_type
            return redirect(url_for("get_home"))



@app.route('/logout')
def logout():
    session.pop('name', default = None)
    session.pop('usertype', default = None)
    session.pop('char_name', default = None)
    return redirect(url_for('get_home'))

def add_course(info):
    course = Courses(
        course_id = info[0],
        instructor = info[1],
        student = info[2],
        exam_type = info[3],
        grades = info[4],
    )
    db.session.add(course)
    db.session.commit()

def add_feedback(info):
    feedback = Feedback(
        q1 = info[0],
        q2 = info[1],
        q3 = info[2],
        q4 = info[3],
        instructor = info[4],
        course_id = info[5]
    )
    db.session.add(feedback)
    db.session.commit()
   
def add_regrade(info):
    regrade = Regrade(
        student = info[0],
        reason = info[1],
        instructor = info[2],
        course_id = info[3]
    )
    db.session.add(regrade)
    db.session.commit()

def add_account(info):
    account = Account(
        username= info[0],
        name = info[1],
        email = info[2],
        password = info[3],
        accountType = info[4],
    )
    db.session.add(account)
    db.session.commit()




if __name__ == '__main__':
    app.run(debug=True)
