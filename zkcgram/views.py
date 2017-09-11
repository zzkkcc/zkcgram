# -*- encoding= UTF-8 -*-
from zkcgram import app, db
from models import Image, User, Comment
from flask import render_template, redirect, request, flash, get_flashed_messages, send_from_directory
from flask_login import login_user, logout_user, current_user, login_required
import random, hashlib, json, uuid, os
from qiniusdk import qiniu_upload_file

# make a route appointment for 首页(a descriptor)
@app.route('/')
def index():
    # render index.html as template(模版), using limit(10) as images
    paginate = Image.query.order_by(db.desc(Image.id)).paginate(page=1, per_page=4, error_out=False)
    return render_template('index.html', images=paginate.items, has_next=paginate.has_next)
# make a route appointment for AJAX
@app.route('/index/images/<int:page>/<int:per_page>/')
def index_images(page, per_page):
    paginate = Image.query.order_by(db.desc(Image.id)).paginate(page=page, per_page=per_page, error_out=False)
    map = {'has_next': paginate.has_next}
    images = []
    for image in paginate.items:
        comments = []
        for i in range(0, min(2, len(image.comments))):
            comment = image.comments[i]
            comments.append({'username': comment.user.username,
                             'user_id': comment.user_id,
                             'content': comment.content})

        imgvo = {'id': image.id,
                 'url':image.url,
                 'comment_count':len(image.comments),
                 'username':image.user.username,
                 'user_id':image.user_id,
                 'head_url':image.user.head_url,
                 'created_date':str(image.created_date),
                 'comments':comments}
        images.append(imgvo)
    map['images'] = images
    return json.dumps(map)

# make a route appointment for 详情页
@app.route('/image/<int:image_id>/')
def image(image_id):
    image = Image.query.get(image_id)
    if image == None:
        return redirect('/')
    return render_template('pageDetail.html', image=image)

# make a route appointment for 个人主页
@app.route('/profile/<int:user_id>/')
# add user access authority
@login_required
def profile(user_id):
    user = User.query.get(user_id)
    if user == None:
        #go back to 首页 if no user_id
        return redirect('/')
    #for original ones, show 3 pages first
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=1, per_page=3, error_out=False)
    return render_template('profile.html', user=user, images=paginate.items, has_next = paginate.has_next)

# AJAX for 个人主页图片部分, AJAX
@app.route('/profile/images/<int:user_id>/<int:page>/<int:per_page>/')
def user_images(user_id, page, per_page):
    paginate = Image.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page, error_out=False)
    map = {'has_next':paginate.has_next}
    images = []
    for image in paginate.items:
        imgvo = {'id':image.id, 'url':image.url, 'comment_count':len(image.comments)}
        images.append(imgvo)
    map['images'] = images
    return json.dumps(map)

# make a route appointment for 登录/注册
@app.route('/regloginpage/')
def regloginpage():
    msg = ''
    for m in get_flashed_messages(with_categories=False, category_filter=['reglogin']):
        msg =msg + m
    return render_template('login.html',msg = msg, next=request.values.get('next'))

def redirect_with_msg(target, msg, category):
    if msg != None:
        flash(msg,category=category)
    return redirect(target)

# make a route appointment for 登录/注册界面
@app.route('/login/', methods= {'post', 'get'})
def login():
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()
    # for error registration scenarios
    if username == '' or password== '':
        #为空，进入错误界面，发送一个信息
        return redirect_with_msg('/regloginpage/',  u'用户名或密码不能为空', 'reglogin')
    # query for username
    user = User.query.filter_by(username=username).first()
    if user == None:
        return redirect_with_msg('/regloginpage/', u'用户名不存在', 'reglogin')
    # adding salt to encode password
    m = hashlib.md5()
    m.update(password+user.salt)
    if(m.hexdigest() != user.password):
        return redirect_with_msg('/regloginpage/', u'密码错误', 'reglogin')
    # get correct username&password, login
    login_user(user)

    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)

    return redirect('/')

# make a route appointment for 注册界面，错误界面下继续进行登录操作
# add post because of html does not support methods initially
@app.route('/reg/', methods={'post','get'})
def reg():
    #parameter in website
    username = request.values.get('username').strip()
    password = request.values.get('password').strip()
    # for error registration scenarios
    if username =='' or password =='':
       return redirect_with_msg('/regloginpage/',  u'用户名或密码不能为空', 'reglogin')
    # query for username
    user = User.query.filter_by(username=username).first()
    if user != None:
        return redirect_with_msg('/regloginpage/', u'用户名已经存在', 'reglogin')
    # adding salt to encode password
    salt = '.'.join(random.sample('0123456789abcdefgABCDEF',10))
    m = hashlib.md5()
    m.update(password+salt)
    #hexadecimal input string as the new password
    password = m.hexdigest()
    user = User(username, password, salt)
    db.session.add(user)
    db.session.commit()
    #login after register
    login_user(user)
    #get request before login, and response to it
    next = request.values.get('next')
    if next != None and next.startswith('/'):
        return redirect(next)
    #does not have any request before login, back to 首页
    return redirect('/')

# make a route appointment for 登出
@app.route('/logout/')
def logout():
    logout_user()
    # return to 首页
    return redirect('/')

#saving method
def save_to_local(file, file_name):
    save_dir = app.config['UPLOAD_DIR']
    file.save(os.path.join(save_dir, file_name))
    return '/image/' + file_name

@app.route('/image/<image_name>')
def view_image(image_name):
    return send_from_directory(app.config['UPLOAD_DIR'], image_name)


#upload to qiniuyun
@app.route('/upload/', methods={"post"})
@login_required
def upload():
    file = request.files['file']
    #ext: 后缀名限制
    file_ext=''
    if file.filename.find('.') > 0:
        #get content after first '.' from right, using lower case letter
        file_ext = file.filename.rsplit('.', 1)[1].strip().lower()
    if file_ext in app.config['ALLOWED_EXT']:
        file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_ext
        url = qiniu_upload_file(file, file_name)
        if url != None:
            db.session.add(Image(url, current_user.id))
            db.session.commit()
    return redirect('/profile/%d' % current_user.id)

'''
#upload to the computer
@app.route('/upload/', methods={"post"})
@login_required
def upload():
    #print request.files
    file = request.files['file']
    file_ext = ''
    if file.filename.find('.') > 0:
        file_ext = file.filename.rsplit('.', 1)[1].strip().lower()
    if file_ext in app.config['ALLOWED_EXT']:
        file_name = str(uuid.uuid1()).replace('-', '') + '.' + file_ext
        url = save_to_local(file, file_name)
        if url != None:
            db.session.add(Image(url, current_user.id))
            db.session.commit()
    return redirect('/profile/%d' % current_user.id)
'''

@app.route('/addcomment/', methods={"post"})
@login_required
def add_comment():
    image_id = int(request.values['image_id'])
    content = request.values['content'].strip()
    comment = Comment(content, image_id, current_user.id)
    db.session.add(comment)
    db.session.commit()
    return json.dumps({"code": 0, id: comment.id,
                       "content": content,
                       "username": comment.user.username,
                       "user_id": comment.user_id})