#####################################
#####################################
#### 2020 WORD ASSASSINS WEBSITE ####
#####################################
#####################################


### The following code is the imported packages ###
from flask import Flask, redirect, url_for, render_template, request, session, abort
import sqlite3, json
import numpy, math


### The following code creates the app variable and assigns a secret key for the session dictionary ###
app = Flask(__name__)
app.secret_key = "this is an arbitrary string"


#### PAGE ROUTING BELOW THIS LINE ####


### index page route. ###
## The main page of the website. Has: personal user input box, create new user button ##
@app.route('/')
def index():
    session['loggedIn'] = False
    session['password'] = ""
    try:
        error = session.pop('error')
    except KeyError:
        error = ""
    try:
        user = session.pop('user')
    except KeyError:
        user = ""
    
    return render_template('index.html', error = error, user = user)


### _login helper route ###
## This helper page is accessed when a personal user is entered from the index page. ##
## It checks that the user is good and then redirects to the home page of the user ##
## If the user is not good, the user is redirected back to the index page with an 'invalid user' message ## 
@app.route('/_login', methods=['POST'])
def _login():
    user = request.form['user']
    session['user'] = user
    password = request.form['password']
    hashPass = password #TODO make hash function
    error = check_for_login_error(user, password)
    if error:
        session['error']=error
        return redirect(url_for('index'))
    else:
        session['loggedIn'] = True
        session['password'] = password
        return redirect(url_for('home'))
            

### signup page route ###
## Page for creating a new user. ##
## Has: user repeatuser and name input boxes, pfp input (TODO), back button (TODO), signup button ## 
@app.route('/signup/')
def signup():
    try:
        error, user, name = session.pop('error'), session.pop('user'), session.pop('name')
    except KeyError:
        error, user, name = "", "", ""
    return render_template('signup.html', error = error, user = user, name = name)


### _signup helper route ###
## This helper page is accessed when info is entered from the signup page. ##
## It checks that the info is good, adds the info to the database, and redirects to the home page ##
@app.route('/_signup', methods = ['POST'])
def _signup():
    user = request.form["user"]
    password = request.form["password"]
    hashPass = password ##TODO this needs to be hashed
    passwordRepeat = request.form["passwordRepeat"]
    name = request.form["name"] 
    games = json.dumps([])
    pastGames = json.dumps([])
    stats = json.dumps({"played": 0, "won": 0, "kills": 0})
    error = check_for_signup_error(user, password, passwordRepeat, name)
    if error:
        session['error']=error
        session['user']=user
        session['name']=name
        return redirect(url_for('signup'))
    else:
        with sqlite3.connect("database.db") as con:  
            cur = con.cursor() 
            cur.execute("INSERT into Players (user, password, name, games, pastGames, stats) values (?, ?, ?, ?, ?, ?)", (user, hashPass, name, games, pastGames, stats))   #creates new user
            con.commit()
        session['loggedIn'] = True
        session['user'] = user
        session['password'] = password
        return redirect(url_for('home'))
   

### home page route ###
## Home page of a specific user ##
## Has: (TODO) welcome, active games, past games, join new and create buttons, edit pf button, logout button ##
@app.route('/home')
def home():
    if not verify_session_logged_in():
        session['error'] = "You cant access home page before logging in!"
        return redirect(url_for('index'))

    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row  
        cur = con.cursor()  

        cur.execute("SELECT * from Players WHERE user = ?", (session['user'], )) 
        name = cur.fetchone()["name"]
        cur.execute("SELECT * from Players WHERE user = ?", (session['user'], )) 
        games = json.loads(cur.fetchone()["games"])
    return render_template('home.html', name=name, user=session['user'], games = games)

### join page ###
@app.route('/join/')
def join():
    if not verify_session_logged_in():
        session['error']="You cant access join page before logging in!"
        return redirect(url_for('index'))

    try:
        error = session.pop('error')
    except KeyError:
        error = ""
    return render_template('join.html', error = error)

### join helper route ###
@app.route('/_join/', methods = ['POST'])
def _join():
    if not verify_session_logged_in():
        session['error']="You cant access _join page before logging in!"
        return redirect(url_for('index'))

    code = request.form['code']
    error = check_for_join_error(code)
    if error:
        session['error'] = error
        return redirect(url_for('join'))
    else:
        with sqlite3.connect("database.db") as con:  
            con.row_factory = sqlite3.Row
            cur = con.cursor() 
            cur.execute("SELECT * from Games WHERE code = ? ", (code, ))
            players = json.dumps(json.loads(cur.fetchone()["players"])+[session['user']]) #adds user to the player list of the game
            cur.execute("UPDATE Games SET players = ? WHERE code = ? ", (players, code))
            cur.execute("SELECT * from Players WHERE user = ? ", (session['user'], ))
            games = json.dumps(json.loads(cur.fetchone()["games"])+[code]) #adds game to the games list of the user
            cur.execute("UPDATE Players SET games = ? WHERE user = ? ", (games, session['user']))
        return redirect(url_for('game', code = code))

### create page ###
@app.route('/create/')
def create():
    if not verify_session_logged_in():
        session['error']="You cant access create page before logging in!"
        return redirect(url_for('index'))
    
    try:
        error, code, name = session.pop('error'), session.pop('code'), session.pop('name')
    except KeyError:
        error, code, name = "", "", ""
    return render_template('create.html', error = error, code = code, name=name)

### _create helper route ###
## This helper page is accessed when info is entered from the create page. ##
## It checks that the info is good, adds the info to the database, and redirects to the game page ##
@app.route('/_create',  methods = ['POST'])
def _create():
    if not verify_session_logged_in():
        session['error']="You cant access _create page before logging in!"
        return redirect(url_for('index'))

    code = request.form["code"]
    name = request.form["name"]
    settings = json.dumps({})
    host = session['user']
    started = 0
    players = json.dumps([session['user']])
    alive = json.dumps([])
    purged = json.dumps([])
    targets = json.dumps({})
    #winner is not set

    error = check_for_create_error(code, name)
    if error:
        session['error'] = error
        session['code'] = code
        session['name'] = name
        return redirect(url_for('create'))
    else:
        with sqlite3.connect("database.db") as con:  
            con.row_factory = sqlite3.Row
            cur = con.cursor() 

            cur.execute("INSERT into Games (code, name, settings, host, started, players, alive, purged, targets) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", (code, name, settings, host, started, players, alive, purged, targets))   #creates new user
            con.commit()

            cur.execute("SELECT * from Players WHERE user = ? ", (session['user'], ))
            games = json.dumps(json.loads(cur.fetchone()["games"])+[code]) #adds game to the games list of the user
            cur.execute("UPDATE Players SET games = ? WHERE user = ? ", (games, session['user']))
        return redirect(url_for('game', code = code))


### game page route ###
## Page for viewing a specific game. Accessible from home page ##
## If user is the host, has: list of players, start button, kick button, back button ##
## If user is not host, has: list of players, leave game button, back button ##
@app.route('/game/<code>')
def game(code):
    if not verify_session_logged_in():
        session['error']="You cant access game page before logging in!"
        return redirect(url_for('index'))
    
    if not verify_user_in_game(session['user'], code):
        return redirect(url_for('home'))

    try:
        error = session.pop('error')
    except KeyError:
        error = ""

    data={}
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        gameRow = cur.execute("SELECT * FROM Games WHERE code = ? ", (code, )).fetchone()
        data['code'] = code
        data['user'] = session['user']
        data['title'] = gameRow['name']
        data['admin'] = (gameRow['host'] == session['user'])
        data['started'] = gameRow['started']
        data['settings'] = gameRow['settings']
        data['host'] = gameRow['host']
        data['players'] = json.loads(gameRow['players'])
        data['numberOfPlayers'] = len(data['players'])
        data['alive'] = json.loads(gameRow['alive'])
        data['purged'] = json.loads(gameRow['purged'])
        if gameRow['started']:
            data['word'] = json.loads(gameRow['targets'])[session['user']]['word']
            data['target'] = json.loads(gameRow['targets'])[session['user']]['target']
        data['isAlive'] = session['user'] in gameRow['alive']


    return render_template('game.html', data = data, error=error)

### _start helper route starts a game that isnt started ###
## only possible by host ##
@app.route('/_start/<code>', methods = ['POST'])
def _start(code):
    if not verify_session_logged_in():
        session['error']="You cant access _start page before logging in!"
        return redirect(url_for('index'))

    if not verify_host(code):
        return redirect(url_for('home'))

    error = check_for_start_error(code)
    if error:
        session['error'] = error
        return redirect(url_for('game', code = code))

    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        row = cur.execute("SELECT * from Games WHERE code = ? ", (code, )).fetchone()
        started = 1
        alive = row['players']
        players = json.loads(row["players"])
        targets = {}
        n=len(players)
        permutation = numpy.random.permutation(n)
        for i in range(n):
            #TODO implement words here
            targets[players[permutation[i]]] = {"word": "word"+str(i), "target": players[permutation[(i+1)%n]], "assassin": players[permutation[i-1]]}
        targets = json.dumps(targets)
        cur.execute("UPDATE Games SET started = ?,  alive = ?, targets = ? WHERE code = ? ", (started, alive, targets, code))
    return redirect(url_for('game', code = code))

### _cancel helper route cancels a game that isn't yet started ###
## only possible by host ##
@app.route('/_cancel/<code>', methods = ['POST'])
def _cancel(code):
    if not verify_session_logged_in():
        session['error']="You cant access _cancel page before logging in!"
        return redirect(url_for('index'))

    if not verify_host(code):
        return redirect(url_for('home'))
    
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        players = json.loads(cur.execute("SELECT * from Games WHERE code = ? ", (code, )).fetchone()['players'])
        for player in players: #delets the game from each players game list
            cur.execute("SELECT * from Players WHERE user = ? ", (player, ))
            games = json.loads(cur.fetchone()["games"])
            games.remove(code) #removes game to the games list of the user
            games = json.dumps(games) 
            cur.execute("UPDATE Players SET games = ? WHERE user = ? ", (games, player))

        cur.execute("DELETE FROM Games WHERE code = ? ", (code, )) #deletes the game from the games database
    return redirect(url_for('home'))


### _kick helper route removes a player from a game that hasn't started ###
## only possible by admin ##
@app.route('/_kick/<code>/<user>', methods = ['POST'])
def _kick(code, user):

    if not verify_session_logged_in():
        session['error']="You cant access _kick page before logging in!"
        return redirect(url_for('index'))

    if not verify_host(code) or not verify_user_in_game(user, code) or user == session['user']:
        session['error']="something is not right! (_kick page error)"
        return redirect(url_for('index'))

    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        cur.execute("SELECT * from Players WHERE user = ? ", (user, ))
        games = json.loads(cur.fetchone()["games"])
        games.remove(code) #removes game from the games list of the user
        games = json.dumps(games) 
        cur.execute("UPDATE Players SET games = ? WHERE user = ? ", (games, user))

        cur.execute("SELECT * from Games WHERE code = ? ", (code, ))
        players = json.loads(cur.fetchone()["players"])
        players.remove(user)  #removes user from the player list of the game
        players = json.dumps(players) 
        cur.execute("UPDATE Games SET players = ? WHERE code = ? ", (players, code))
    return redirect(url_for('game', code = code))
    
@app.route('/_killed/<code>', methods = ['POST'])
def _killed(code):
    if not verify_session_logged_in():
        session['error']="You cant access _killed page before logging in!"
        return redirect(url_for('index'))
    
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        user = session['user']
        row = cur.execute("SELECT * from Games WHERE code = ? ", (code, )).fetchone()
        alive = json.loads(row["alive"])
        alive.remove(user)  #removes user from the alive list of the game
        alive = json.dumps(alive)
        targets = json.dumps(edit_targets_on_kill(user, json.loads(row['targets'])))
        cur.execute("UPDATE Games SET alive = ?, targets = ? WHERE code = ? ", (alive, targets, code))
    return redirect(url_for('game', code = code))

### purge page for purging a player by game host ###
@app.route('/_purge/<code>/<user>', methods = ['POST'])
def _purge(code, user):
    if not verify_session_logged_in():
        session['error']="You cant access _purge page before logging in!"
        return redirect(url_for('index'))

    if not verify_host(code) or not verify_user_in_game(user, code) or user == session['user']:
        session['error']="something is not right! (_purge)"
        return redirect(url_for('index'))

    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        row = cur.execute("SELECT * from Games WHERE code = ? ", (code, )).fetchone()
        alive = json.loads(row["alive"])
        alive.remove(user)  #removes user from the alive list of the game
        alive = json.dumps(alive)
        purged = json.dumps(json.loads(row["purged"])+[user]) #adds user to the purged list of the game
        targets = json.dumps(edit_targets_on_kill(user, json.loads(row['targets'])))
        cur.execute("UPDATE Games SET alive = ?, targets = ?, purged = ? WHERE code = ? ", (alive, targets, purged, code))

    return redirect(url_for('game', code = code))


#### HELPER FUNCTIONS BELOW THIS LINE ####

### verfier that a user is logged in on a page ###
def verify_session_logged_in():
    if not (session.get('loggedIn') and session.get('user') and session.get('password')): #checks that loggedIn and user session variables exist
        return False
    with sqlite3.connect("database.db") as con:  #checks that the user is an actual user in the database
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        if cur.execute("SELECT count(*) FROM Players WHERE user = ? ", (session['user'], )).fetchone()[0] == 0: #checks that user exists 
            return False
        if cur.execute("SELECT * FROM Players WHERE user = ? ", (session['user'], )).fetchone()['password'] != session['password']: # checks that passwords match TODO: hashpass
            return False
    return session['loggedIn'] #makes sure logged in variable is set to true

### verifies that a user is an actual player in the game ###
def verify_user_in_game(user, code):
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        if cur.execute("SELECT count(*) FROM Games WHERE code = ? ", (code, )).fetchone()[0] == 0:
            return False
        return user in cur.execute("SELECT * FROM Games WHERE code = ? ", (code, )).fetchone()['players']

## verifies that the session user is the host ##
def verify_host(code):
        with sqlite3.connect("database.db") as con:  
            con.row_factory = sqlite3.Row
            cur = con.cursor() 
            if cur.execute("SELECT count(*) FROM Games WHERE code = ? ", (code, )).fetchone()[0] == 0:
                return False
            return session['user'] == cur.execute("SELECT * FROM Games WHERE code = ? ", (code, )).fetchone()['host']

### verifier that checks that a user is good to log in with. makes sure it's long and is in the database ###
## returns an error message if there is an error. False if there is no error ##
def check_for_login_error(user, password):
    if len(user) < 5:
        return "The username can't be less than 5 characters long"
    if len(password) < 5:
        return "The password can't be less than 5 characters long"
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        if cur.execute("SELECT count(*) FROM Players WHERE user= ? ", (user, )).fetchone()[0] == 0: #checks that username exsts
            return "no such user exists"
        if cur.execute("SELECT * FROM Players WHERE user = ? ", (session['user'], )).fetchone()['password'] != session['password']: # checks that passwords match TODO: hashpass
            return "The username or password is wrong"
    return  False
        
### verifier that checks that a username, password and name are good to sign up with. makes sure it's long and is in the database ###
## returns an error message if there is an error. False if there is no error ##
def check_for_signup_error(user, password, passwordRepeat, name):
    #TODO: check that the username only contains normal characters
    if len(user) < 5:
        return "The username can't be less than 5 characters long."
    if len(user) > 20:
        return "The username can't be more than 20 characters long."
    if len(password) < 5:
        return "The password can't be less than 5 characters long."
    if password != passwordRepeat:
        return "The passwords must match."
    if len(name.strip()) == 0:
        return "You must have a name!"
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        if cur.execute("SELECT count(*) FROM Players WHERE user= ? ", (user, )).fetchone()[0] > 0:
            return "Oh no! Someone already took this username."
    return  False

### verifier that checks that a code is good to join with. makes sure it's an actual game and that the user is not already in the game ###
## returns an error message if there is an error. False if there is no error ##
def check_for_join_error(code):
    if not code:
        return "please enter a game code"
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        if cur.execute("SELECT count(*) FROM Games WHERE code = ? ", (code, )).fetchone()[0] == 0:
            return "no such game exists" 
        row =  cur.execute("SELECT * FROM Games WHERE code = ? ", (code, )).fetchone()
        if row['started']:
            return "this game has already started"
        if session['user'] in row['players']:
            return "you are already in this game"
    return False

### verifier that checks that a code and name are good to c with. makes sure code is long enough, name is non empty, and that the game doesnt already exist ###
## returns an error message if there is an error. False if there is no error ##
def check_for_create_error(code, name):
    if len(code)<5:
        return "game code must be at least 5 characters long"
    if len(name.strip())==0:
        return "your game must have a name"
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row
        cur = con.cursor() 
        if cur.execute("SELECT count(*) FROM Games WHERE code = ? ", (code, )).fetchone()[0] > 0:
            return "a game with this code already exists"
    return False

def check_for_start_error(code):
    with sqlite3.connect("database.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        if len(json.loads(cur.execute("SELECT * FROM Games WHERE code= ? ", (code, )).fetchone()["players"])) < 2:
            return "You need at least 2 players to play!"
    return False

### modifies the targets map after user is killed ###
def edit_targets_on_kill(user, targets):
    targets[targets[user]['assassin']]['word'], targets[user]['word'] = targets[user]['word'], targets[targets[user]['assassin']]['word'] #swaps words with the assassin
    targets[targets[user]['assassin']]['target'] = targets[user]['target'] #changes assassin's target
    targets[targets[user]['target']]['assassin'] = targets[user]['assassin'] #changes target's assassin
    targets[user]['target'] = targets[user]['assassin'] #sets target to assassin
    return targets


#### DEBUG CODE BELOW THIS LINE ####

### debugging page with database tables ###
@app.route('/debug/')
def debug():
    with sqlite3.connect("database.db") as con:  
        con.row_factory = sqlite3.Row  
        cur = con.cursor()  

        cur.execute("SELECT * from Players")   
        playerRows = cur.fetchall()   #rows of the Players table

        cur.execute("SELECT * from Games")   
        gameRows = cur.fetchall()   #rows of the Games table

        cur.execute("SELECT * from pastGames")   
        pastRows = cur.fetchall()   #rows of the pastGames table

    return render_template('debug.html', playerRows = playerRows, gameRows = gameRows, pastRows=pastRows)

#### MAIN APP RUN BELOW THIS LINE ####

if __name__ == "__main__":
    app.run(debug = True) #set debug to false if you don't want auto updating