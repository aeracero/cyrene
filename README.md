# Railway デプロイ軽量化版

## 適用
既存リポジトリのルートに Dockerfile、requirements.txt、.dockerignore、cyrene.py をコピーしてください。既存の3ファイルは置き換え、.dockerignore は追加です。独自の .dockerignore がある場合は内容を統合してください。他のPythonファイルとvoicesフォルダは既存のものを使用します。このZIPだけではBot全体にはなりません。このREADMEは説明用なのでリポジトリにコピーする必要はありません。

.dockerignore は隠しファイルです。MacのFinderでは Command + Shift + . で表示できます。4ファイルをGitHubへ反映すると、連携中のRailwayでビルドされます。

初回は構成が変わるため再構築されます。以降、依存ファイルが変わらずRailway側でレイヤーキャッシュが利用できれば、コードのみの変更では依存インストールを再利用できます。

## 原因候補
現在の音声コードは外部TTS APIへリクエストして、返った音声をFFmpegで再生します。しかし元のビルドではtorch、torchaudio、transformers、TTS、cutlet、fugashi、unidic-lite、imageio-ffmpegと日本語解析・ローカル合成用OSパッケージを導入していました。全Pythonソースを確認した限り、これらは使われていません。大規模依存の取得・解決・展開とイメージ転送が遅延の有力候補です。Railwayログと時間計測は未確認で、何分短縮するかは未確定です。

元のDockerfileも requirements.txt → pip install → COPY . . の順序は適切でした。コード変更のたびに必ずpipが再実行されるという診断ではありません。また --no-cache-dir はpipのダウンロードキャッシュの指定で、Dockerレイヤーキャッシュを無効化する指定ではありません。

## 変更点
- 未使用のローカル音声モデル依存、MeCab、espeak-ng、開発用コンパイラ等を削除。
- FFmpeg、Opus、PyNaClを維持。外部TTS API方式の読み上げを維持。
- google-generativeaiはTRPG等で使われるため維持。aiohttpを明示的に追加。
- Python 3.10を維持し、Debian bookwormを明示。OS推奨パッケージの追加を抑制。
- .dockerignoreでGit履歴、仮想環境、ログ、.env等をビルド対象から除外。voicesとアプリ用JSONは保持。
- Pythonログを即時出力。
- Discord再接続時のコマンド再同期を省略。プロセス起動後の初回同期と、同期失敗後の再試行は維持。
- 直前に作成した反復検索・根拠照合・出典リンク・長文分割版cyrene.pyを同梱。
- 現在GitHubで指定されているgemini-3.8-flashを既定値として維持。GEMINI_MODEL_NAME環境変数があればそちらを優先。

## 設定
既存のDISCORD_TOKEN、GEMINI_API_KEY、TTS_API_URLと永続ボリュームの設定を保持してください。このrequirements.txtはRailwayのBot専用です。ローカルの音声生成サーバーには適用しないでください。

RESEARCH_TIMEOUT_SECONDSは既定300秒。0なら時間制限なしです。検索回数の固定上限はなく、根拠が揃うか進展がなくなるまで追加検索します。複数回のAI呼び出しによる待ち時間・料金はビルド軽量化とは別です。

## 検証・制限
Python構文チェック、全Pythonのimport照合、調査処理の6件の模擬テストを実施。Docker実行環境がないため、コンテナビルド、新しい依存のインストール、Discord/Gemini/TTSとの実通信は未検証です。一部依存は元の方針と同じく未固定です。初回成功後に実環境の解決済みバージョンを固定すると再現性が向上します。

まだ遅い場合はBuild LogsとDeployment Logsで時間がかかる工程を確認してください。
- Queued: ビルド待ち。依存削減だけでは改善しない場合があります。
- pip install: 新requirements.txtが使われているか確認。
- export/push/pull: イメージ転送。今回の軽量化が効く可能性があります。
- 起動後のDeploying: 再起動、起動コマンド、ヘルスチェック等。このBotはHTTPサーバーではないので、HTTPヘルスチェックを設定している場合は整合性を確認してください。

トークン等の秘密情報を除いた該当ログがあれば、残る原因を特定できます。

参考: https://docs.docker.com/build/cache/optimize/ 、 https://docs.railway.com/builds/dockerfiles
