from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def menu():
    return render_template('menu.html')

# 共通ログインページ：役割だけ変える
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    return render_template('login.html', role='教員')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    return render_template('login.html', role='児童')

# 3枚目（教員新規登録）はそのままでOK
@app.route('/teacher/signup', methods=['GET', 'POST'])
def teacher_signup():
    if request.method == 'POST':
        # ここに実処理（バリデーション/DB/Firebaseなど）を追加予定
        pass
    return render_template('teacher_signup.html')

if __name__ == '__main__':
    app.run(debug=True)
