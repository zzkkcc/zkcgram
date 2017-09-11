# -*- encoding= UTF-8 -*-
#
from zkcgram import app, db
from flask_script import Manager
from zkcgram.models import User, Image, Comment
import random, unittest

manager = Manager(app)

def get_image_url():
    return 'http://images.nowcoder.com/head/' + str(random.randint(0,1000)) + 'm.png'
# '@' is a descriptor to record functions information, such as times of running,etc

@manager.command
def run_test():
    db.drop_all()
    db.create_all()
    tests = unittest.TestLoader().discover('./')
    unittest.TextTestRunner().run(tests)

@manager.command
def init_database():
    db.drop_all()
    db.create_all()
    for i in range(0,100):
        db.session.add(User('User' + str(i),'a'+str(i+1)))
        for j in range(0,10):
            db.session.add(Image(get_image_url(),i+1))
            for k in range(0,3):
                db.session.add(Comment('cao ni ma' + str(k),1+10*i+j,i+1))

    db.session.commit()

    for i in range(50, 100, 2):#renew data
        user = User.query.get(i)
        user.username = '[NEW]' + user.username

    User.query.filter_by(id=51).update({'username':'[New2]'})
    db.session.commit()

    for i in range(50,100,2):#delete function
        comment = Comment.query.get(i+1)#search first
        db.session.delete(comment)
    db.session.commit()

    #print 1, User.query.all()
    print 2, User.query.get(3)
    #print 3, User.query.order_by(User.id.desc()).paginate(page=1, per_page=10).items
    user = User.query.get(1)
    print 4, user.images


if __name__ == '__main__':
    manager.run()
