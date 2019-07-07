from flask import Flask, request #import main Flask class and request object

app = Flask(__name__) #create the Flask app

@app.route('/query-example')
def query_example():
    return 'Todo...'

@app.route('/form-example')
def formexample():
    return 'Todo...'

@app.route('/set_speed', methods=['POST'])
def set_speed():
    req_data = request.get_json()
    token = req_data['token']
    speed = req_data['speed']

    res = 'the speed is now {}'.format(speed)
    print('DEBUG:',res)
    return res

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0') #run app in debug mode on port 5000
