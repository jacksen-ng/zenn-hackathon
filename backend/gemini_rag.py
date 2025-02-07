import os
import nltk
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.memory import ChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import MessagesPlaceholder
from langchain_core.runnables import chain
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, trim_messages, filter_messages
from operator import itemgetter
from langchain_core.runnables import RunnableLambda
from langchain.docstore.document import Document

# 必要なnltkデータをダウンロード
nltk.download('punkt')


class Gemini_RAG:
    """
    Gemini_RAG_Memory は、
    ・ ドキュメントのロードと分割
    ・ ベクトルストアへの格納とリトリーバー作成
    ・ チャット履歴を考慮した質問の再構成と回答生成
    を担当するクラスです。

    Attributes:
        api_key (str): APIキー（.env から読み込み）
        model_name (str): モデル名（.env から読み込み）
        documents (list): 読み込んだドキュメント
        list_ (list): chunk split後のテキストのリスト
        vectorstore: FAISSなどのベクトルストアインスタンス
        retriever: ベクトルストアから生成したリトリーバ
        contextualize_chain: チャット履歴に基づく質問再構成チェーン
        qa_chain: 質問に対して最終回答を行うチェーン
        qa_with_history (RunnableWithMessageHistory): チャット履歴管理付きの Runnable
    """

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        self.model_name = os.getenv('MODEL')

        self.documents = None
        self.list_ = []
        self.vectorstore = None
        self.retriever = None
        self.contextualize_chain = None
        self.qa_chain = None
        self.qa_with_history = None
        self.current_document = None  # Track current document path
        self.is_initialized = False

    def _text_splitter(
        self,
        chunk_size: int = 100,
        chunk_overlap: int = 70
    ):
        print("text_splitterが呼び出されました")
        """
        ドキュメントを指定したchunkサイズ・重なり量で分割し、テキストのリストを生成する
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        texts = text_splitter.create_documents([self.documents[0].page_content])
        self.list_ = [text.page_content for text in texts]

    def _vector_store(self):
        """
        テキストをベクトル化してFAISSに格納する
        """
        self.vectorstore = FAISS.from_texts(
            self.list_,
            embedding=HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        )

    def _retriever(self, k: int = 8):
        """
        ベクトルストアからリトリーバーを作成する
        """
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})

    def _get_msg_content(self, msg):
        print("get_msg_contentが呼び出されました")
        """
        メッセージオブジェクトから実際のテキスト（content）だけを抽出する
        """
        return msg.content

    def save_text(self, content: str, chunk_size: int = 100, chunk_overlap: int = 70):
        """Load and process document content directly"""
        print(f"Attempting to process text content")
        
        if not content:
            raise ValueError("Document content cannot be empty")
            
        try:
            self._process_text(content)
            self._text_splitter(chunk_size, chunk_overlap)
            self._vector_store()
            self._retriever()
            self.is_initialized = True
            print(f"Successfully processed document content")
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            raise

    def _process_text(self, content: str):
        """
        テキスト内容を直接処理する
        """
        try:
            # ドキュメントオブジェクトを作成
            self.documents = [Document(page_content=content)]
            print(f"Document content processed successfully")
            print(f"Document content length: {len(content)}")
        except Exception as e:
            print(f"Error processing text content: {str(e)}")
            raise

    def _trimmer(self, input_messages):
        trimmer = trim_messages(
        max_tokens=3,
        strategy="last",
        token_counter=len,
        include_system=True,
        allow_partial=True,
        start_on="human",
        )
        trimmed_messages = trimmer.invoke(input_messages)
        session_history = self.histories[f"{self.now_session}"]
        session_history.messages = trimmed_messages

    def get_session_history(self, session_id: str=''):
        if session_id not in self.histories:
            self.histories[session_id] = InMemoryChatMessageHistory()
        return self.histories[session_id]

    def _preparation_prompt(self):
        """
        ユーザーの質問を再構成するContextualize Chainと、
        文脈を取り込んだ最終回答を生成するQA Chainを定義する
        """
        llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            api_key=self.api_key
        )

        # 再構成用システムプロンプト
        contextualize_system_prompt = """
        チャット履歴と最新のユーザーの質問を与えられた場合、
        チャット履歴の文脈を参照する必要があるため、
        理解できるような質問に再構成してください。
        チャット履歴がなければ質問に答えないでください。
        ただ必要に応じて再構成し、そのまま返してください。
        """

        contextualize_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])
        self.contextualize_chain = (
            contextualize_prompt
            | llm
            | self._get_msg_content
        )

        # QA用システムプロンプト
        qa_system_prompt = """
        あなたは優秀なAIアシスタントです。
        以下の取得された文脈を使用して質問に答えてください。
        もし答えがわからない場合は、その旨を伝えてください。
        3つの文を上限にして、簡潔に答えてください。
        \n\n
        {context}
        """

        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ])

        @chain
        def wrapper_for_trim(input_messages):
            return self._trimmer(input_messages)


        self.qa_chain = (
        RunnablePassthrough().assign(
            messages=itemgetter("chat_history")
        | wrapper_for_trim)
        | qa_prompt
        | llm
        | self._get_msg_content
    )

    def _history_aware_qa(self, input_: dict):
        """
        実際の質問応答処理:
        RunnableWithMessageHistoryから渡される辞書を受け取り、
        チャット履歴を考慮した再構成を行ってからリトリーバ検索 + QA実行
        """

        if input_.get("chat_history"):
            question = self.contextualize_chain.invoke(input_)
        else:
            question = input_["input"]

        context = self.retriever.invoke(question)

        return self.qa_chain.invoke({
            **input_,
            "context": context,
        })

    def _preparation_run(self):
        """
        RunnableWithMessageHistoryを生成し、qa_with_history属性へ格納する
        """

        @chain
        def wrapper_for_chain(input_: dict):
            return self._history_aware_qa(input_)

        self.qa_with_history = RunnableWithMessageHistory(
            wrapper_for_chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def run(self):
        """
        QA実行に最低限必要なチェーンなどの準備を行う
        """
        self.histories: dict[str, InMemoryChatMessageHistory] = {}
        self._preparation_prompt()
        self._preparation_run()


    def ask(self, prompt: str, session_id: str) -> str:
        self.now_session = session_id
        """
        チャット履歴管理（RunnableWithMessageHistory）付きのQAを実行し、回答を返す
        """
        return self.qa_with_history.invoke(
            {"input": prompt},
            config={"configurable": {"session_id": session_id}}
        )