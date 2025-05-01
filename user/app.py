# app.py
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from Model import db
from Model.user import User

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
    get_jwt
)
from flask_jwt_extended.exceptions import JWTExtendedException
from datetime import  timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']        = 'postgresql://ouma:passwordouma@userDb:5432/user'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY']                 = 'oumayma oumayma'
app.config['JWT_ACCESS_TOKEN_EXPIRES']       = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES']      = timedelta(days=30)

# Initialisation de l'ORM et du JWT
# Assure-toi que 'db' a déjà été instancié et configuré dans your_existing_package
db.init_app(app)
jwt = JWTManager(app)

with app.app_context():
    db.create_all()
    default_admin_email = 'admin@example.com'
    if not User.query.filter_by(email=default_admin_email).first():
        admin = User(
            first_name='Admin',
            last_name='User',
            email=default_admin_email,
            password_hash=generate_password_hash('Admin@123'),
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}

    for field in ('first_name', 'last_name', 'email', 'password', 'role'):
        if not data.get(field):
            return jsonify({'error': f'Le champ {field} est requis'}), 400

    pw_hashed = generate_password_hash(data['password'])

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email déjà enregistré'}), 409

    user = User(
        first_name    = data['first_name'],
        last_name     = data['last_name'],
        email         = data['email'],
        password_hash = pw_hashed,
        role          = "employée",
        is_active     = False
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'id'         : user.id,
        'first_name' : user.first_name,
        'last_name'  : user.last_name,
        'email'      : user.email,
        'role'       : user.role,
        'is_active'  : user.is_active,
        'created_at' : user.created_at.isoformat()
    }), 201

@app.route('/api/users/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email    = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email et mot de passe requis'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Identifiants invalides'}), 401

    additional_claims = {
        'user_id'    : user.id,
        'email'      : user.email,
        'first_name' : user.first_name,
        'last_name'  : user.last_name,
        'role'       : user.role,
        'is_active'  : user.is_active
    }
    access_token  = create_access_token(identity=str(user.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

    return jsonify({
        'access_token' : access_token,
        'refresh_token': refresh_token
    }), 200

@app.route('/api/users/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_access_token():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    additional_claims = {
        'user_id'    : user.id,
        'email'      : user.email,
        'first_name' : user.first_name,
        'last_name'  : user.last_name,
        'role'       : user.role,
        'is_active'  : user.is_active
    }
    new_access_token = create_access_token(identity=user.id, additional_claims=additional_claims)
    return jsonify({'access_token': new_access_token}), 200

@app.route('/api/users/token/verify', methods=['GET'])
def verify_token():
    try:
        verify_jwt_in_request()
        return jsonify({'valid': True}), 200
    except JWTExtendedException:
        return jsonify({'valid': False}), 200

@app.route('/api/users/confirm/<int:user_id>', methods=['POST'])
@jwt_required()
def confirm_user(user_id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Permission refusée, administrateur requis'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    if user.is_active:
        return jsonify({'message': 'Compte déjà activé'}), 200

    user.is_active = True
    db.session.commit()
    return jsonify({'message': 'Compte activé avec succès'}), 200

# Endpoint de mise à jour d'un utilisateur existant
@app.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        return jsonify({'error': 'Permission refusée, identifiant utilisateur non correspondant'}), 403

    data = request.get_json() or {}
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    for field in ('first_name', 'last_name', 'email', 'role', 'is_active'):
        if field in data:
            if field == 'email' and User.query.filter_by(email=data['email']).first() and data['email'] != user.email:
                return jsonify({'error': 'Email déjà enregistré'}), 409
            setattr(user, field, data[field])

    db.session.commit()
    return jsonify({
        'id'         : user.id,
        'first_name' : user.first_name,
        'last_name'  : user.last_name,
        'email'      : user.email,
        'role'       : user.role,
        'is_active'  : user.is_active,
        'updated_at' : user.updated_at.isoformat()
    }), 200

# Endpoint de suppression d'un utilisateur
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        return jsonify({'error': 'Permission refusée, identifiant utilisateur non correspondant'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'Utilisateur supprimé avec succès'}), 200
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_all_users():
    users = User.query.all()
    return jsonify([
        {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat()
        } for user in users
    ]), 200

# Endpoint pour récupérer un utilisateur par ID
@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_by_id(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    return jsonify({
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat()
    }), 200
if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True,port=5000)
