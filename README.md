# Zenn-Hackathon

武蔵野大学データサイエンス学部BohPJ同好会に所属する人がzenn-hackathonに挑む。メンバー：

- ウン　ジャックセン
- 高橋快成
- 大田原直生
- 室秀磨

## Usage

```python
from gemini_rag import Gemini_RAG

# 1)インスタンス作成，RAGのモデルを読み込みます．
chatbot = Gemini_RAG()

# 2) ドキュメントを読み込んでベクトルストア化します．
# pathに読ませたいドキュメントのpathを指定します．
chatbot.save_text(path="rag.txt")

# 3) チェーンなどの初期化
# ベクトルストア以降の初期化処理をここで行います．
chatbot.run()

### この3つの処理を最初に行ってください．

# 4) ユーザーの入力後，回答を出力します．
# inputの例とsession_idの例を示します．どちらもstr型です．
chatbot.ask("このドキュメントには何が書いてありますか？", session_id="123")

# 5) 4)を必要に応じて使ってください．sessionを変えることで，チャット履歴を初期化できます，
```
