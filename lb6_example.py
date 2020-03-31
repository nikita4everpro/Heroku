import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String

engine = create_engine('sqlite:///bot.db')
connection = engine.connect()

metadata = sqlalchemy.MetaData()
Users = sqlalchemy.Table('Users', metadata, autoload=True, autoload_with=engine)
Words = sqlalchemy.Table('Words', metadata, autoload=True, autoload_with=engine)
Examples = sqlalchemy.Table('Examples', metadata, autoload=True, autoload_with=engine)
Answers = sqlalchemy.Table('Answers', metadata, autoload=True, autoload_with=engine)

'''
query = sqlalchemy.select([Words, Answers])
query = query.select_from(Words.join(Answers, Words.columns.word_id == Answers.columns.word_id))
ResultProxy = connection.execute(query)
ResultSet = ResultProxy.fetchall()
print(ResultSet)
'''
#query = sqlalchemy.insert(Users).values(full_name='naveen', viber_id='gdffghfgfdgd', time_last_answer=sqlalchemy.sql.func.now())
#ResultProxy = connection.execute(query)
'''
query = sqlalchemy.select([Users]).where(Users.columns.viber_id == 'gdvvffghfgfdgd')
ResultProxy = connection.execute(query)
ResultSet = ResultProxy.fetchone()
print(ResultSet)

query = sqlalchemy.update(Users).values(viber_id = "100000")
query = query.where(Users.columns.viber_id == 'gdffghfgfdgd')
results = connection.execute(query)
'''

query = sqlalchemy.select([Words]).order_by(sqlalchemy.sql.func.random()).limit(5)
ResultProxy = connection.execute(query)
ResultSet = ResultProxy.fetchall()
print(ResultSet)


