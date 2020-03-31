from flask import Flask, request, Response
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages import VideoMessage
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.messages.keyboard_message import KeyboardMessage
import logging

from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberFailedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from viberbot.api.viber_requests import ViberUnsubscribedRequest

import json
import random
import sqlite3
import sqlalchemy
from sqlalchemy import create_engine


class MyDateBase:
    def __init__(self, database_name):
        engine = create_engine(database_name)
        self.connection = engine.connect()

        metadata = sqlalchemy.MetaData()
        self.Users = sqlalchemy.Table('Users', metadata, autoload=True, autoload_with=engine)
        self.Words = sqlalchemy.Table('Words', metadata, autoload=True, autoload_with=engine)
        self.Examples = sqlalchemy.Table('Examples', metadata, autoload=True, autoload_with=engine)
        self.Answers = sqlalchemy.Table('Answers', metadata, autoload=True, autoload_with=engine)

    def close(self):
        self.connection.close()

    def add_user(self, user_name, viber_id):
        query = sqlalchemy.insert(self.Users).values(full_name=user_name, viber_id=viber_id, time_last_answer=sqlalchemy.sql.func.now())
        self.connection.execute(query)


    def check_user(self, viber_id):
        query = sqlalchemy.select([self.Users]).where(self.Users.columns.viber_id == viber_id)
        ResultProxy = self.connection.execute(query)
        if ResultProxy.fetchone() == None:
            return False
        else:
            return True

    def get_user_id(self, viber_id):
        query = sqlalchemy.select([self.Users.columns.user_id]).where(self.Users.columns.viber_id == viber_id)
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def get_user_name(self, viber_id):
        query = sqlalchemy.select([self.Users.columns.full_name]).where(self.Users.columns.viber_id == viber_id)
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def add_word(self, word, translate):
        query = sqlalchemy.insert(self.Words).values(word=word, translate=translate)
        self.connection.execute(query)

    def get_word_id(self, word):
        query = sqlalchemy.select([self.Words.columns.word_id]).where(self.Words.columns.word == word)
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def count_studied_word_by_user(self, user):
        user_id = self.get_user_id(user)
        query = sqlalchemy.select([sqlalchemy.func.count(self.Answers)]).where(sqlalchemy.and_(self.Answers.columns.user_id == user_id, self.Answers.columns.count_right >= 5))
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def count_education_word_by_user(self, user):
        user_id = self.get_user_id(user)
        query = sqlalchemy.select([sqlalchemy.func.count(self.Answers)]).where(sqlalchemy.and_(self.Answers.columns.user_id == user_id, self.Answers.columns.count_right != None))
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def example_for_word(self, word):
        query = sqlalchemy.select([self.Examples.columns.example])
        query = query.select_from(self.Examples.join(self.Words, self.Examples.columns.word_id == self.Words.columns.word_id))
        query = query.where(self.Words.columns.word == word)
        query = query.order_by(sqlalchemy.sql.func.random()).limit(5)
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]


    def get_time_last_answer_user(self, user):
        query = sqlalchemy.select([self.Users.columns.time_last_answer]).where(self.Users.columns.viber_id == user)
        ResultProxy = self.connection.execute(query)
        return ResultProxy.fetchone()[0]

    def get_random_words_for_user(self, user):
        user_id = self.get_user_id(user)

        queryPod = sqlalchemy.select([self.Answers]).where(self.Answers.columns.user_id == user_id)
        podQuery = queryPod.cte()
        query = sqlalchemy.select([self.Words.columns.word, self.Words.columns.translate])
        query = query.select_from(self.Words.outerjoin(podQuery, self.Words.columns.word_id == podQuery.columns.word_id))
        query = query.where(sqlalchemy.or_(podQuery.columns.count_right < 5, podQuery.columns.count_right == None))
        query = query.order_by(sqlalchemy.sql.func.random()).limit(5)
        ResultProxy = self.connection.execute(query)
        rez = []
        for word in ResultProxy.fetchall():
            rez.append({"Word": word[0], "Translate": word[1]})

        print(rez)
        return rez



    def get_random_3_words_without(self, without):
        query = sqlalchemy.select([self.Words.columns.translate]).where(self.Words.columns.word != without)
        query = query.order_by(sqlalchemy.sql.func.random()).limit(3)
        ResultProxy = self.connection.execute(query)
        rez= [ResultProxy.fetchone()[0], ResultProxy.fetchone()[0], ResultProxy.fetchone()[0]];
        print(rez)
        return rez

    def change_right_word_for_user(self, word, user):
        self.check_answer_user_word_and_add(word, user)
        word_id = self.get_word_id(word)
        user_id = self.get_user_id(user)

        query = sqlalchemy.select([self.Answers.columns.count_right]).where(sqlalchemy.sql.and_(self.Answers.columns.word_id == word_id,self.Answers.columns.user_id==user_id))
        ResultProxy = self.connection.execute(query)
        count = ResultProxy.fetchone()[0]

        query = sqlalchemy.update(self.Answers).values(count_right=count+1, time_last_answer=sqlalchemy.sql.func.now())
        query = query.where(sqlalchemy.sql.and_(self.Answers.columns.word_id == word_id, self.Answers.columns.user_id == user_id))
        self.connection.execute(query)

    def change_wrong_word_for_user(self, word, user):
        self.check_answer_user_word_and_add(word, user)
        word_id = self.get_word_id(word)
        user_id = self.get_user_id(user)

        query = sqlalchemy.update(self.Answers).values(time_last_answer=sqlalchemy.sql.func.now())
        query = query.where(sqlalchemy.sql.and_(self.Answers.columns.word_id == word_id, self.Answers.columns.user_id == user_id))
        self.connection.execute(query)


    def check_answer_user_word_and_add(self, word, user):
        word_id = self.get_word_id(word)
        user_id = self.get_user_id(user)

        query = sqlalchemy.select([self.Answers]).where(sqlalchemy.sql.and_(self.Answers.columns.word_id == word_id, self.Answers.columns.user_id == user_id))
        ResultProxy = self.connection.execute(query)
        if ResultProxy.fetchone() != None:
            return
        else:
            query = sqlalchemy.insert(self.Answers).values(word_id=word_id, user_id=user_id, count_right=0)
            self.connection.execute(query)

    def update_user_last_data(self, user_id):
        query = sqlalchemy.update(self.Users).values(time_last_answer=sqlalchemy.sql.func.now())
        query = query.where(self.Users.columns.user_id == user_id)
        self.connection.execute(query)



db = MyDateBase('sqlite:///bot.db?check_same_thread=false')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)

bot_configuration = BotConfiguration(
    name='nkita4everPRO',
    avatar='http://viber.com/avatar.jpg',
    auth_token='4abd77ef3d67d55a-26d6cbab559873d7-dff915e69db779f1'
)
viber = Api(bot_configuration)

TestLength = 3
DictUserFind = {}

EngWords = json.load(open('engWords.txt', encoding='utf-8'))
KeysTask = json.load(open('keyboardTask.txt', encoding='utf-8'))
KeysStart = json.load(open('keyboardStart.txt', encoding='utf-8'))


@app.route('/', methods=['POST'])
def incoming():
    logger.debug("received request. post data: {0}".format(request.get_data()))

    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return Response(status=403)

    viber_request = viber.parse_request(request.get_data())

    #print(viber_request)

    if isinstance(viber_request, ViberMessageRequest):
        message = viber_request.message.text.split()
        viber_id = viber_request.sender.id

        CheckUser(viber_request.sender.name, viber_id)

        try:
        #if 1==1:
            if message[0] == '/start':
                DictUserFind[viber_id] = {"Words": [], "OtherWords": [], "Count": 0, "Points": 0, "Length": 0}
                DictUserFind[viber_id]["Words"] = db.get_random_words_for_user(viber_id)
                #print(DictUserFind[viber_id]["Words"])
                DictUserFind[viber_id]["Length"] = len(DictUserFind[viber_id]["Words"])


                GenNewTask(viber_id)
                SetKeysTask(viber_id)
                viber.send_messages(viber_id, [
                    TextMessage(text="Как переводится с английского слово '"+DictUserFind[viber_id]['Words'][DictUserFind[viber_id]['Count']]['Word']+"'?"),
                    KeyboardMessage(keyboard=KeysTask)
                ])
            elif message[0] == '/example':
                SetKeysTask(viber_id)

                viber.send_messages(viber_id, [
                    TextMessage(text=db.example_for_word(DictUserFind[viber_id]['Words'][DictUserFind[viber_id]['Count']]['Word'])),
                    KeyboardMessage(keyboard=KeysTask)
                ])

            # Ответ верный
            elif message[0] == DictUserFind[viber_id]['Words'][DictUserFind[viber_id]['Count']]['Translate']:
                CheckAndNextTask(viber_id, True)

            # Ответ неверный
            else:
                CheckAndNextTask(viber_id, False)

        except:
            CheckUserAndStartMessage(viber_request.sender.name, viber_request.sender.id)


    elif isinstance(viber_request, ViberSubscribedRequest):
        CheckUserAndStartMessage(viber_request.user.name, viber_request.user.id)

    elif isinstance(viber_request, ViberConversationStartedRequest):
        CheckUserAndStartMessage(viber_request.user.name, viber_request.user.id)

    elif isinstance(viber_request, ViberUnsubscribedRequest):
        print("User ", viber_request.user_id, " unsubscribed")

    return Response(status=200)


# Генерация нового задания
def GenNewTask(viber_id):
    DictUserFind[viber_id]['OtherWords'] = db.get_random_3_words_without(DictUserFind[viber_id]['Words'][DictUserFind[viber_id]['Count']]['Word'])

# Проверка на выполнение и выдача следующего задания
def CheckAndNextTask(id, isCorrect):
    DictUserFind[id]['Count'] += 1
    MessIsCorr = ""

    if isCorrect:
        DictUserFind[id]['Points'] += 1
        MessIsCorr = "Верный ответ\n"
        db.change_right_word_for_user(DictUserFind[id]['Words'][DictUserFind[id]['Count']-1]['Word'], id)
    else:
        MessIsCorr = "Неверный ответ\n"
        db.change_wrong_word_for_user(DictUserFind[id]['Words'][DictUserFind[id]['Count']-1]['Word'], id)

    if DictUserFind[id]['Count'] < DictUserFind[id]['Length']:
        GenNewTask(id)
        SetKeysTask(id)
        viber.send_messages(id, [
            TextMessage(text=MessIsCorr + "Как переводится с английского слово '" + DictUserFind[id]['Words'][DictUserFind[id]['Count']]['Word'] + "'?"),
            KeyboardMessage(keyboard=KeysTask)
        ])
    elif DictUserFind[id]['Count'] == DictUserFind[id]['Length']:
        print("END!")
        viber.send_messages(id, [
            TextMessage(text=MessIsCorr + "Вы набрали " + str(DictUserFind[id]['Points']) + " из " + str(DictUserFind[id]['Length']) + " баллов!"),
            KeyboardMessage(keyboard=KeysStart)
        ])
    else:
        StartMessage(id)

# Формирование кнопок
def SetKeysTask(id):
    nwordinkey = random.randint(0, 3)
    otherN = 0
    random.shuffle(DictUserFind[id]['OtherWords'])
    nword = DictUserFind[id]['Count']
    for i in range(4):
        if (i == nwordinkey):
            KeysTask['Buttons'][i]['Text'] = DictUserFind[id]['Words'][nword]['Translate']
            KeysTask['Buttons'][i]['ActionBody'] = DictUserFind[id]['Words'][nword]['Translate']
        else:
            KeysTask['Buttons'][i]['Text'] = DictUserFind[id]['OtherWords'][otherN]
            KeysTask['Buttons'][i]['ActionBody'] = DictUserFind[id]['OtherWords'][otherN]
            otherN += 1

# Стартовое сообщение с описанием
def StartMessage(id):
    user_name = db.get_user_name(id)
    viber.send_messages(id, [
        TextMessage(text="Привет, " + user_name + "!\n" +
                         "Изучали: " + str(db.count_education_word_by_user(id)) + " слов\n" +
                         "Выучено: " + str(db.count_studied_word_by_user(id)) + " слов\n" +
                         "Последний раз отвечали: " + str(db.get_time_last_answer_user(id)) + "\n" +
                         "Бот создан для заучивания английских слов. Для начала теста нажмите на кнопку внизу или введите /start"),
        KeyboardMessage(keyboard=KeysStart)
    ])

# Добавление нового пользователя и вывод стартового сообщения
def CheckUserAndStartMessage(name, id):
    if db.check_user(id)==False:
        db.add_user(name,id)
    StartMessage(id)

# Добавление пользователя
def CheckUser(name, id):
    if db.check_user(id)==False:
        db.add_user(name,id)


app.run(host='127.0.0.1', port=5000)

