# Fairness → binding
# ライブラリをインポート
import streamlit as st
from streamlit_chat import message

from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import pytz
import time

#現在時刻
global now
now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

# 環境変数の読み込み
#from dotenv import load_dotenv
#load_dotenv()

#プロンプトテンプレートを作成
template = """
今からチャットボットと私で会話のロールプレイをしましょう。
設定は以下の通りです。

テーマ：
日本は原子力発電を廃止すべきか否か

シナリオ：
チャットボットと私は同じ日本の大学に通い、同じ講義を受けている大学生になりきります。
今、講義の途中、先生が、二人組でグループワークをするよう指示しました。
二人でテーマについて、対等な関係で自分の意見を主張し、簡単な議論をします。
お互いチャット上の匿名のやりとりになります。

ゴール：
私たちの隠れた目的は、お互いの意見を交換し、共通点と相違点を明らかにすることです。
積極的に意見を主張したり、反論や、問いかけ、質問をしたりするなどして、会話してください。

事前知識：
・道徳基盤理論について
道徳基盤理論(Moral Foundations Theory)についてはご存知ですね。
Haidtの道徳基盤理論では5つの基盤が存在します。
また道徳基盤理論は、イデオロギーや社会問題と関連する知見もあります。
社会問題に関する会話や意見において、道徳基盤は価値判断、意見、他者への反応を決定します。

チャットボットのロール：
・名前　佐藤
・日本の大学に通う一般的な大学生
・｢ですます｣口調
・カジュアルでリラックスした口調
・原子力発電の廃止に賛成
上記の設定に加え、この人は、以下のチャットボットの道徳基盤に従って議論をします。

チャットボットの道徳基盤：
5つの道徳基盤のうち、HarmとFairnessの基盤の感受性が、一般よりも特に高い人です。
よって個人の福祉と他者の権利を尊重し、他者や社会制度による危害や不当な扱いから個人を守ることに焦点をあてます。

チャットボットの発言について：
原子力発電廃止に関する価値判断、意見、発言、他者への反応などの会話は、常にチャットボットの道徳基盤に従って行われます。

私のロール：
チャットボットの話し相手
・名前は不明
･名古屋大学に通う一般的な大学生
その他については指定はありません。

チャットボットへの指示：
上記の設定を踏まえて、私とステップバイステップで会話してください。
一回の回答につき、日本語で100文字以内で回答してください。
小学生でも分かる平易かつフランクな言葉遣いで、主観的に回答してください。
自分の道徳基盤や道徳基盤理論に関することは一切明かさないでください。
名前を聞かれたら、秘密であると答えてください。
AIだとばれないよう振る舞ってください。
別れの挨拶の時は｢ありがとうございました！｣とのみ返してください。
もし、私が原子力発電廃止に賛成の立場をとっても、チャットボットも原子力発電廃止に賛成の立場のまま、議論は続けてください。
では、私から話し始めます。
"""

# 会話のテンプレートを作成
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(template),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{input}"),
])

#会話の読み込みを行う関数を定義
#@st.cache_resource
#def load_conversation():
    #llm = ChatOpenAI(
        #model_name="gpt-4",
        #temperature=0
    #)
    #memory = ConversationBufferMemory(return_messages=True)
    #conversation = ConversationChain(
        #memory=memory,
        #prompt=prompt,
        #llm=llm)
    #return conversation
model_select = "gpt-4-1106-preview"
#st.write(model_select)
# デコレータを使わない会話履歴読み込み for セッション管理
def load_conversation():
    if not hasattr(st.session_state, "conversation"):
        llm = ChatOpenAI(
            #model_name="gpt-4",
            #model_name="gpt-4",
            model_name=model_select,
            temperature=0
        )
        memory = ConversationBufferMemory(return_messages=True)
        st.session_state.conversation = ConversationChain(
            memory=memory,
            prompt=prompt,
            llm=llm)
    return st.session_state.conversation

# 質問と回答を保存するための空のリストを作成
if "generated" not in st.session_state:
    st.session_state.generated = []
if "past" not in st.session_state:
    st.session_state.past = []
    
# 会話のターン数をカウント
if 'count' not in st.session_state:
    st.session_state.count = 0

if 'number' not in st.session_state:
    st.session_state.number = 0

# 送信ボタンがクリックされた後の処理を行う関数を定義
def on_input_change():
    # 会話のターン数をカウント
    #if 'count' not in st.session_state:
    #    st.session_state.count = 0
    st.session_state.count += 1
    # n往復目にプロンプトテンプレートの一部を改めて入力
    #if  st.session_state.count == 3:
    #    api_user_message = st.session_state.user_message + "。そして、これ以降の会話では以前の語尾を廃止して、語尾をにゃんに変えてください"
    #else:
    #    api_user_message = st.session_state.user_message

    user_message = st.session_state.user_message
    conversation = load_conversation()
    with st.spinner("相手からの返信を待っています。。。"):
        #if  st.session_state.count == 1:
            #time.sleep(120)
        #elif st.session_state.count == 2:
            #time.sleep(90)
        #elif st.session_state.count == 3:
            #time.sleep(105)
        #elif st.session_state.count == 4:
            #time.sleep(90)
        #elif st.session_state.count == 5:
            #time.sleep(90)
        #else :
            #time.sleep(3)
        time.sleep(1)
        answer = conversation.predict(input=user_message)
    st.session_state.generated.append(answer)
    st.session_state.past.append(user_message)

    st.session_state.user_message = ""
    Human_Agent = "Human" 
    AI_Agent = "AI" 
    turn_count = "count"
    doc_ref = db.collection(user_number).document(str(now))
    doc_ref.set({
        Human_Agent: user_message,
        AI_Agent: answer,
        turn_count: st.session_state.count
    })

# qualtricdへURL遷移
def redirect_to_url(url):
    new_tab_js = f"""<script>window.open("{url}", "_blank");</script>"""
    st.markdown(new_tab_js, unsafe_allow_html=True)

# タイトルやキャプション部分のUI
# st.title("ChatApp")
# st.caption("Q&A")
# st.write("議論を行いましょう！")
user_number = st.text_input("参加者番号を半角で入力してエンターを押してください")
if user_number:
    # st.write(f"こんにちは、{user_number}さん！")
    # 初期済みでない場合は初期化処理を行う
    if not firebase_admin._apps:
            cred = credentials.Certificate('chatnextin-firebase-adminsdk-tj4wu-db6ea15eef.json') 
            default_app = firebase_admin.initialize_app(cred)
    db = firestore.client()
    st.session_state.number = 1
    #doc_ref = db.collection(user_number)
    #doc_ref = db.collection(u'tour').document(str(now))

# 会話履歴を表示するためのスペースを確保
chat_placeholder = st.empty()

# 会話履歴を表示
with chat_placeholder.container():
    for i in range(len(st.session_state.generated)):
        message(st.session_state.past[i],is_user=True, key=str(i), avatar_style="adventurer", seed="Nala")
        key_generated = str(i) + "keyg"
        message(st.session_state.generated[i], key=str(key_generated), avatar_style="micah")

# 質問入力欄と送信ボタンを設置
if  st.session_state.number == 1:
    with st.container():
        if  st.session_state.count == 0:
            user_message = st.text_input("「原子力発電は廃止すべき」という意見に対して、あなたの意見を入力して送信ボタンを押してください", key="user_message")
            st.button("送信", on_click=on_input_change)
        elif st.session_state.count >= 5:
            st.write("意見交換はこちらで終了です。")
            redirect_link = "https://nagoyapsychology.qualtrics.com/jfe/form/SV_1M3cjOQM09gOcEC"
            st.markdown(f'<a href="{redirect_link}" target="_blank">こちらを押してください。</a>', unsafe_allow_html=True)
        else:
            user_message = st.text_input("あなたの意見を入力して送信ボタンを押してください", key="user_message")
            st.button("送信", on_click=on_input_change)
# 質問入力欄 上とどっちが良いか    
#if user_message := st.chat_input("聞きたいことを入力してね！", key="user_message"):
#    on_input_change()


#redirect_link = "https://nagoyapsychology.qualtrics.com/jfe/form/SV_1M3cjOQM09gOcEC"
#st.markdown(f'<a href="{redirect_link}" target="_blank">5往復のチャットが終了したらこちらを押してください。</a>', unsafe_allow_html=True)
#if st.button("終了したらこちらを押してください。画面が遷移します。"):
    #redirect_to_url("https://www.google.com")

hide_streamlit_style = """
                <style>
                div[data-testid="stToolbar"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stDecoration"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                div[data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
                }
                #MainMenu {
                visibility: hidden;
                height: 0%;
                }
                header {
                visibility: hidden;
                height: 0%;
                }
                footer {
                visibility: hidden;
                height: 0%;
                }
                </style>
                """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
