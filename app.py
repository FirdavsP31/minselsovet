import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timedelta
from flask_cors import CORS 
from werkzeug.utils import secure_filename


app = Flask(__name__)
CORS(app) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, nullable=False)
    sender_name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    attachment = db.Column(db.String(100), nullable=True)
    attachment_type = db.Column(db.String(20), nullable=True)


messages = []
chat_stats = {
    'total_users': set(),
    'online_users': {},
    'first_seen': {}
}

@app.route('/')
def index():
    return render_template('chat.html')




@app.route('/api/chat_stats', methods=['POST'])
def handle_chat_stats():
    data = request.get_json()
    user_id = str(data['user_id'])
    now = datetime.now()
    is_new = False


    if user_id not in chat_stats['total_users']:
        is_new = True
        chat_stats['total_users'].add(user_id)
        chat_stats['first_seen'][user_id] = now


    if data.get('is_online', True):
        chat_stats['online_users'][user_id] = now
    else:
        chat_stats['online_users'].pop(user_id, None)


    expired = now - timedelta(seconds=1)
    chat_stats['online_users'] = {
        uid: ts for uid, ts in chat_stats['online_users'].items()
        if ts > expired
    }


    return jsonify({
        'online': len(chat_stats['online_users']),
        'total': len(chat_stats['total_users']),
        'new': is_new
    })

@app.route('/api/update_activity', methods=['POST'])
def update_activity():
    user_id = str(request.json.get('user_id', ''))
    
    if user_id and user_id in chat_stats['online_users']:
        return jsonify({
            'online': len(chat_stats['online_users']),
            'total': chat_stats['total_users']
        })
    
    return jsonify({'status': 'error'}), 400

@app.route('/api/set_offline', methods=['POST'])
def set_offline():
    user_id = str(request.json.get('user_id', ''))
    
    if user_id and user_id in chat_stats['online_users']:
        chat_stats['online_users'].remove(user_id)
    
    return jsonify({'status': 'success'})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    try:
        last_id = request.args.get('last_id', default=0, type=int)
        tg_user_id = request.args.get('tg_user_id', default=0, type=int)
        
        messages = Message.query.filter(Message.id > last_id).order_by(Message.timestamp.asc()).all()
        
        return jsonify([{
            'id': m.id,
            'sender': m.sender_name,
            'content': m.content,
            'time': m.timestamp.strftime('%H:%M'),
            'is_me': m.sender_id == tg_user_id,
            'attachment': m.attachment
        } for m in messages])
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/send', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        message = Message(
            sender_id=data.get('tg_user_id'),
            sender_name=data.get('sender_name'),
            content=data['content']
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'time': message.timestamp.strftime('%H:%M')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400



@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    try:
        message_id = int(request.json['id'])
        message = Message.query.get(message_id)
        
        if not message:
            return {'success': False, 'error': 'Message not found'}, 404
            
        db.session.delete(message)
        db.session.commit()
        return {'success': True}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}, 500



@app.route('/api/send_file', methods=['POST'])
def send_file_message():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().timestamp()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            message = Message(
                sender_id=request.form.get('tg_user_id'),
                sender_name=request.form.get('sender_name'),
                content=request.form.get('content', ''),
                attachment=unique_filename,
                attachment_type=file.content_type
            )
            
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'time': message.timestamp.strftime('%H:%M'),
                'message_id': message.id,
                'attachment': unique_filename
            })
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<filename>')
def get_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)