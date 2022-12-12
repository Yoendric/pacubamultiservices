from flask import Flask, render_template, url_for, redirect, session, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from wtforms.fields import DateField
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from datetime import timedelta, datetime, date
import os
import secrets
from waitress import serve


load_dotenv()
reference_hour = 20 ## 8:00 pm referencia de cerrar el viaje

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1Oropesa2.@localhost/pacubamultiservices'
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

################################################   LOGIN ##################################################
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    Nombre = db.Column(db.String(20), nullable=False)
    Apellido = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(20), nullable=True)
    

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
                             
    Nombre = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Name"})
    
    Apellido = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Last"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(                                                      #####  Here  #####
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash("Wrong Password - Try Again!")
        else:
            flash("That User Doesn't Exist! Try Again...")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password, 
                    Nombre=form.Nombre.data, Apellido=form.Apellido.data, type='user')
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
#############################################  LOGIN END  #######################################################
#############################################  CALENDAR INIT ####################################################
def day_array_calendar():
    weekDays = ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday") 
    month = ("January","February","March","April","May","June","July","August","September","October","November","December")
    thisXMasDay = datetime.now().weekday()
    today = datetime.now()
    last_day_month_before = (today-timedelta(days=datetime.now().day))
    init_day = last_day_month_before-timedelta(days=last_day_month_before.weekday())
    day_array = list()
    while init_day <= today:
        day_array.append(init_day)
        init_day+=timedelta(days=1)
    while init_day.month == today.month:
        day_array.append(init_day)
        init_day+=timedelta(days=1)
    while init_day.weekday() != 0:
        day_array.append(init_day)
        init_day+=timedelta(days=1)
    return [weekDays[thisXMasDay],month[datetime.now().month - 1], datetime.now(), day_array]

class FechaForm(FlaskForm):
    dt = DateField('DatePicker', format='%Y-%m-%d')

class Calendar(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    FECHA = db.Column(db.String(20), nullable=False, unique=True)

@app.route('/calendar', methods=['GET', 'POST'])
@login_required
def calendar():
    user = User.query.filter_by(id=current_user.id).first()
    form = FechaForm() #//Instanciamos la clase
    day_array = day_array_calendar()        
    if request.method == 'POST':
        if datetime.strptime(request.form.get('dt'), "%Y-%m-%d") > datetime.now():
            check_duplicate = Calendar.query.filter_by(FECHA = request.form.get('dt')).first()
            if not check_duplicate:
                new_calendar = Calendar(FECHA=request.form.get('dt'))
                db.session.add(new_calendar)
                db.session.commit()
            else:
                flash("Fecha de Viaje ya Salvada")
        else:
            flash("Fecha de Viaje Agregada anterior a Fecha actual")
    calendar = Calendar.query.filter(Calendar.FECHA >= date.today()).limit(3).all()
    return render_template("calendar.html", user=user,form=form, day=day_array, calendar=calendar)

#############################################  CLIENT  ##########################################################
class Client(db.Model):
    codigo = db.Column(db.String(10), primary_key=True)
    remitente = db.Column(db.String(50), nullable=False)
    cell_remitente = db.Column(db.String(20),nullable=False)
    destinatario = db.Column(db.String(50), nullable=False)
    cell_destinatario = db.Column(db.String(20),nullable=False)
    address = db.Column(db.String(100),nullable=False)
    municipio = db.Column(db.String(20),nullable=False)
    provincia =  db.Column(db.String(30),nullable=False)
    nota = db.Column(db.String(100),nullable=True)

class Aduana(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.Integer,nullable=False)

class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article = db.Column(db.String(50), nullable=False)
    cost_by_unit = db.Column(db.Float,nullable=False)
    condicion = db.Column(db.Integer,nullable=False) 

class Packet(db.Model):
    tracking_number = db.Column(db.String(15), primary_key=True)
    codigo = db.Column(db.String(10), nullable=False)
    ship = db.Column(db.Integer, nullable=False)
    Sale = db.Column(db.String(35),nullable=False)
    Miscelanea_libras = db.Column(db.Float,nullable=False)
    Costo_miscelanea = db.Column(db.Float,nullable=False)
    AseoComidaMedicina_libras = db.Column(db.Float,nullable=False)
    Costo_aseocomidamedicina = db.Column(db.Float,nullable=False)
    Piezas = db.Column(db.String(100),nullable=False)
    Costo_piezas = db.Column(db.Float,nullable=False)
    Total_estimado = db.Column(db.Float,nullable=False)
    Total_cobrado = db.Column(db.Float,nullable=False)
    status = db.Column(db.String(15),nullable=True)
    notas = db.Column(db.String(100),nullable=True)
    time = db.Column(db.String(30), nullable=False)
    balance = db.Column(db.Boolean, nullable=False)
    
def cost_unit_include_if_have_offer(request):
    cost = list()
    articles = ["micelanea","me-aseo-com","telefono","tablet","laptop"]
    for i in articles:
        query = Offer.query.filter(Offer.article == i,Offer.condicion <= request.form.get(i)).order_by(Offer.condicion.desc()).first()
        cost.append(query.cost_by_unit)
    return cost
    
def estimation_cost_packet(request):
    cost_unit = cost_unit_include_if_have_offer(request)
    lib_micelanea = float(request.form.get('micelanea'))
    cost_lib_micelanea = cost_unit[0]
    lib_me_aseo_com = float(request.form.get('me-aseo-com'))
    cost_lib_me_aseo_com = cost_unit[1]
    amount_phone = int(request.form.get('telefono'))
    cost_unit_phone = cost_unit[2]
    amount_tablet = int(request.form.get('tablet'))
    cost_unit_tablet = cost_unit[3]
    amount_laptop = int(request.form.get('laptop'))
    cost_unit_laptop = cost_unit[4]
    art=Aduana.query.filter_by(article=request.form.get('article')).first()
    if art:
        point = int(art.cost)
        a = request.form.get('article')
    else:
        point = 0
        a = None
    other = float(request.form.get('other'))
    array_cost = [ round(lib_micelanea * cost_lib_micelanea,2),
                   round(lib_me_aseo_com * cost_lib_me_aseo_com,2),
                   amount_phone * cost_unit_phone,
                   amount_tablet * cost_unit_tablet,
                   amount_laptop * cost_unit_laptop,
                   point,
                   other]
    array_cost.append(sum(array_cost))
    array_cost.append([lib_micelanea, lib_me_aseo_com, amount_phone, amount_tablet, amount_laptop, a])
    return array_cost

def string_piezas_packet(request):
    string_element = ["telefono","tablet","laptop"]  ##### Other Element should been aggregate
    string_word =''
    for i in string_element:
        if request.form.get(i) != '0':
            string_word += request.form.get(i) +' '+i + '/'
    if request.form.get('article') != '0':
        string_word += '1' +' '+ request.form.get('article') + '/'
    return(string_word)
    
    
def assign_client_code(query):
    Init_pack={"Palmira":'P',"Cienfuegos":'C',"Mayabeque":'Y',"Artemisa":'A',"La Habana":'H',
               "Sancti Spiritus":'S',"Villa Clara":'V',"Matanzas":'M',"Pinar del Rio":'R'}
    if query.get("mun")=="Palmira":    
        obj = Client.query.filter_by(municipio=query.get("mun")).order_by(Client.codigo.desc()).first()
        if obj:
            return Init_pack["Palmira"]+str(int(obj.codigo[1:])+1)
        else:
            return Init_pack["Palmira"]+'000'
    elif query.get("Cienfuegos"):
        obj = Client.query.filter_by(provincia="Cienfuegos").order_by(Client.codigo.desc()).all()
        if obj:
            for i in obj:
                if i.codigo[0]==Init_pack[query.get("pro")]:
                    return Init_pack[query.get("pro")]+str(int(i.codigo[1:])+1)
        return Init_pack[query.get("pro")]+'000'
    else:
        obj = Client.query.filter_by(municipio=query.get("mun")).order_by(Client.codigo.desc()).first()
        if obj:
            return Init_pack[query.get("pro")]+str(int(obj.codigo[1:])+1)
        else:
            return Init_pack[query.get("pro")]+'000'

@app.route('/paqueteria', methods=['GET', 'POST'])
@login_required
def paqueteria():
    user = User.query.filter_by(id=current_user.id).first()
    if request.method == 'GET':
        return render_template('packet.html',user=user)    ######### First Search
    else:
        if request.form.get("button"):                     ######### New User Add button
            return render_template('sender.html',user=user)
        elif request.form.get("addUser"):                  ######### Add User 
            if request.form.get("codigo"):
                codigo=request.form.get("codigo")
            else:
                obj = Client.query.filter_by(address=request.form.get("address"),destinatario=request.form.get("destinatario")
                            ,cell_remitente=request.form.get("cell_remitente")).all()
                if obj:
                    codigo=obj[0].codigo
                else:
                    codigo=assign_client_code(request.form)
                    new_client = Client(codigo=codigo, remitente=request.form.get("remitente"),
                    cell_remitente = request.form.get("cell_remitente"), destinatario=request.form.get("destinatario"),
                    cell_destinatario = request.form.get("cell_destinatario"), address = request.form.get("address"),                  
                    municipio = request.form.get("mun"), provincia=request.form.get("pro"))
                    db.session.add(new_client)
                    db.session.commit()
            flash("Codigo de Client: {}".format(codigo))    ########
            return redirect(url_for('character_packet', codigo=codigo)) ######## Page Second  next   #############HERE HERE HERE
        elif request.form.get("select"):                   ####SELECT ELEMENT FINDING#####
            if len(request.form) == 2:                      ######## No select any element
                flash("No select any Client-sender")
                return render_template('packet.html',user=user)
            if len(request.form) > 3:
                flash("Selected more than one client-sender")######## Select most one element
                return render_template('packet.html',user=user)  
            else:
                obj = Client.query.filter_by(codigo=request.form.get('1')).all()   #### Select OK
                return render_template('sender.html',user=user,obj=obj)             
        else:                                                ######## FIND Client
            obj = Client.query.filter_by(cell_remitente=request.form.get("search")).all()
            if not obj:
                obj = Client.query.filter_by(codigo=request.form.get("search")).all()
                if not obj:
                    flash("No user found with that description")
                else:
                    return render_template('sender.html',user=user,obj=obj)
            if len(obj)== 1:
                return render_template('sender.html',user=user,obj=obj)
            return render_template('packet.html',user=user,obj=obj)

@app.route('/character_packet', methods=['GET', 'POST'])
@login_required
def character_packet():
    user = User.query.filter_by(id=current_user.id).first()
    point_article = Aduana.query.filter(Aduana.id >= 4).all()
    if request.method == 'GET':
        codigo = request.args.get('codigo')
        return render_template('character_packet.html',user=user,hidden=codigo,point_article=point_article)
    else:
        codigo = request.form.get('codigo')
        if request.form.get('estimar_packet'):
            estimacion=estimation_cost_packet(request)
            return render_template('character_packet.html',user=user,hidden=codigo,point_article=point_article,valor=estimacion)
        if request.form.get('registrar_packet'):
            reference_day = date.today()
            if datetime.now().hour >= reference_hour: 
                reference_day += timedelta(days=0.5)
            try:
                query = Calendar.query.filter(Calendar.FECHA > reference_day).first()
                if query:
                    number_ship = query.id
                else:
                    query = Calendar.query.order_by(Calendar.id.desc()).first()
                    number_ship = query.id + 1
            except:
                number_ship = 1
            number_packet = request.form.get('codigo') + 'V{}'.format(number_ship)
            packet = Packet.query.filter_by(tracking_number=number_packet).first()
            if packet:
                number_packet += '_' + datetime.now().strftime("%M%S")
            datos = request.form.get('costos').replace('[','')
            datos= [float(x) for x in datos[:-2].split(',')[:-1]]
            string_piezas_packet(request)
            new_packet = Packet(tracking_number = number_packet,
                                codigo = request.form.get('codigo'),
                                ship = number_ship,
                                Sale = current_user.username,
                                Miscelanea_libras = datos[8],
                                Costo_miscelanea = datos[0],
                                AseoComidaMedicina_libras = datos[9],
                                Costo_aseocomidamedicina = datos[1],
                                Piezas = string_piezas_packet(request),
                                Costo_piezas = datos[2] + datos[3] + datos[4] + datos[5] + datos[6],
                                Total_estimado = datos[7],
                                Total_cobrado = float(request.form.get('total')),
                                status = 'Recibido',
                                notas = request.form.get('note'),
                                time = datetime.now(),
                                balance = False) 
            db.session.add(new_packet)
            db.session.commit()                  
            flash("Paquete Guardado, Numero de paquete: {}".format(number_packet))            
            return render_template('end_process.html',user=user)
        return render_template('character_packet.html',user=user,hidden=codigo,point_article=point_article)
    

#############################################  CLIENT END ######################################################

def view_data():
    reference_day = date.today()
    if datetime.now().hour >= reference_hour: 
        reference_day += timedelta(days=0.5)
    try:
        query = Calendar.query.filter(Calendar.FECHA > reference_day).first()
        if query:
            number_ship = query.id
            day = query.FECHA
        else:
            query = Calendar.query.order_by(Calendar.id.desc()).first()
            number_ship = query.id + 1
            day = 'Desconocido'
    except:
        number_ship = 1
        day = 'Desconocido'
    packet = Packet.query.filter(Packet.ship == number_ship).all()
    dinero_total = 0
    numero_packet = 0
    numero_libras = 0
    lib_mic = 0
    lib_mac = 0
    user = dict()
    if packet:
        for pack in packet:  
            if pack.Sale in user:
                user[pack.Sale][0] += 1
                user[pack.Sale][1] += pack.Total_cobrado
                user[pack.Sale][2] += pack.Miscelanea_libras
                user[pack.Sale][3] += pack.AseoComidaMedicina_libras
            else:
                user[pack.Sale] = [ 1, pack.Total_cobrado, pack.Miscelanea_libras, pack.AseoComidaMedicina_libras]   
            dinero_total += pack.Total_cobrado
            numero_libras += pack.Miscelanea_libras + pack.AseoComidaMedicina_libras
            lib_mic += pack.Miscelanea_libras
            lib_mac += pack.AseoComidaMedicina_libras
            numero_packet += 1
    if user:
        print("Hay usuarios")
    return ([number_ship,day,numero_packet, numero_libras,lib_mic,lib_mac,dinero_total,user])

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = User.query.filter_by(id=current_user.id).first()
    return render_template('index.html',user=user)
    
@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    user = User.query.filter_by(id=current_user.id).first()
    return render_template('report.html',user=user,resumen=view_data())
    
#############################################  USER  ###########################################################

@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    user = User.query.filter_by(id=current_user.id).first()
    return render_template('user.html',user=user)
    
@app.route('/user_change', methods=['GET', 'POST'])
@login_required
def user_change():
    list_user = list()
    user_group = User.query.all()
    for i in user_group:
        list_user.append(i.username)
    list_user.remove('admin')
    user = User.query.filter_by(id=current_user.id).first()
    if request.method == 'GET':
        return render_template('userchange.html',user=user,users=list_user)
    else:
        if request.form.get("user") == None:
            flash("No User Selected")
        else:
            obj = User.query.filter_by(username=request.form.get("user")).one()
            if request.form.get("button") == "delete":
                db.session.delete(obj)
                db.session.commit()
                flash("User {} erased sucefully".format(request.form.get("user")))
            elif request.form.get("button") == "change":
                rows_updated = User.query.filter_by(username=request.form.get("user")).update(dict(type=request.form.get("permiso")))
                db.session.commit()
                flash("User update sucefully")
            else:
                return render_template('user.html',user = user,obj = obj)
        return render_template('userchange.html',user=user,users=list_user)    
    
################################################################################################################

if __name__ == "__main__":
    app.run(debug=True)
    #serve(app, host='0.0.0.0', port=8000, threads=1) #WAITRESS!
