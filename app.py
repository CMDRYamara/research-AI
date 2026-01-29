import streamlit as st
import google.generativeai as genai
from tavily import TavilyClient
import time

# --- 設定: ページ構成 ---
st.set_page_config(page_title="VC Insight Agent", layout="wide")

st.title("自律型AI 競合リサーチアプリケーション")
st.markdown("""
ターゲット企業のURLを入力すると、
**AIが自律的にWeb検索を行い、競合他社を特定し、比較分析レポートを作成**します。
""")

# --- サイドバー: APIキー設定 (デモ用) ---
with st.sidebar:
    st.header("⚙️ API Key Settings")
    gemini_key = st.text_input("Gemini API Key", value="AIzaSyBVR0Jz5Lm2iykQg8J77Gy8J0mmvo5IW28", type="password")
    # value にキーを入れ、type は "password" にします
    tavily_key = st.text_input("Tavily API Key", value="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", type="password")
    
    st.info("※デモ用にキーを直接入力できます。本番環境では環境変数で管理します。")

# --- メインロジック ---

def run_research_agent(target_url, product_name):
    # 1. APIクライアントの初期化
    genai.configure(api_key=gemini_key)
    # 分析・推論には賢い "gemini-1.5-pro" を推奨（Flashより少し遅いが精度が高い）
    # Flashは高速なのでデモ向きです
    model = genai.GenerativeModel('gemini-3-flash-preview')
    tavily = TavilyClient(api_key=tavily_key)

    result_container = st.container()

    # --- Step 1: ターゲット企業の分析 (Webブラウジング) ---
    with st.status("Step 1: ターゲット企業を調査中...", expanded=True) as status:
        st.write(f"URL ({target_url}) にアクセスして情報を取得しています...")
        
        # Tavilyでターゲットサイトの情報を取得
        # search_depth="advanced" で深く読む
        target_search = tavily.search(query=f"What is {product_name}? site:{target_url}", search_depth="advanced")
        target_context = target_search.get("results", [])
        
        # Geminiに「これは何の会社か？」を理解させる
        target_summary_prompt = f"""
        以下の検索結果に基づいて、'{product_name}' のビジネスモデル、主要機能、ターゲット顧客を300文字以内で要約してください。
        
        [検索結果]:
        {target_context}
        """
        response_step1 = model.generate_content(target_summary_prompt)
        target_summary = response_step1.text
        
        st.success("ターゲット企業の主要情報を抽出しました。")
        st.markdown(f"**概要:** {target_summary}")
        
        status.update(label="Step 1: 完了 (ターゲット分析済み)", state="complete", expanded=False)

    # --- Step 2: 競合の特定 (推論 + 検索) ---
    with st.status("Step 2: 競合他社を特定・検索中...", expanded=True) as status:
        st.write("AIが適切な検索クエリを生成し、競合を探しています...")
        
        # 競合を探すためのクエリをGeminiに考えさせる
        query_gen_prompt = f"""
        '{product_name}' は以下のようなサービスです: {target_summary}
        
        このサービスの直接的な競合(Competitors)や代替サービスを探すための、
        **最適なGoogle検索クエリを1つだけ** 出力してください。
        余計な文章は不要です。クエリのみを出力してください。
        例: "{product_name} alternatives competitors"
        """
        search_query_response = model.generate_content(query_gen_prompt)
        search_query = search_query_response.text.strip()
        
        st.code(f"Generated Query: {search_query}")
        
        # Tavilyで競合を検索
        st.write("Web全体から競合情報を収集中...")
        competitor_search = tavily.search(query=search_query, search_depth="advanced", max_results=5)
        competitor_context = competitor_search.get("results", [])
        
        st.success("競合らしき企業のデータを取得しました。")
        status.update(label="Step 2: 完了 (競合データ収集済み)", state="complete", expanded=False)

    # --- Step 3: 比較レポートの生成 (統合・分析) ---
    with st.status("Step 3: 比較マトリクスレポートを執筆中...", expanded=True) as status:
        st.write("収集したデータを整理し、Markdown形式でレポートを作成しています...")
        
        final_prompt = f"""
        あなたはトップティアのベンチャーキャピタリストのアソシエイトです。
        以下の情報に基づき、投資検討のための「競合比較レポート」を作成してください。
        
        【ターゲット企業 ({product_name}) の情報】
        {target_summary}
        {target_context}
        
        【検索された競合他社の情報】
        {competitor_context}
        
        【出力フォーマット】
        1. **Executive Summary**: この市場の状況とターゲット企業の立ち位置（200文字）
        2. **Competitive Matrix**: ターゲット企業を含む主要3〜4社の比較表を作成してください。
           - 列: 企業名, 価格モデル, 主な特徴, ターゲット層, 強み/弱み
        3. **Moat Analysis (参入障壁)**: 
           - ターゲット企業が競合に対して勝てる要素（Moat）はあるか？辛口に評価してください。
        4. **Due Diligence Questions**: 
           - 代表面談で確認すべき、競合優位性に関する鋭い質問を3つ。
        
        ※日本語で出力してください。Markdownの表形式を使用してください。
        """
        
        final_response = model.generate_content(final_prompt)
        
        status.update(label="Step 3: 完了 (レポート作成)", state="complete", expanded=False)
        
        return final_response.text

# --- UI入力部分 ---
col1, col2 = st.columns([1, 2])
with col1:
    target_product = st.text_input("企業名/サービス名", placeholder="例: Notion")
with col2:
    target_url = st.text_input("URL (任意)", placeholder="例: https://www.notion.so")

if st.button("🚀 調査エージェントを起動", type="primary"):
    if not gemini_key or not tavily_key:
        st.error("サイドバーにAPIキーを入力してください。")
    elif not target_product:
        st.error("企業名を入力してください。")
    else:
        try:
            # 実行
            report = run_research_agent(target_url, target_product)
            
            # 結果表示
            st.divider()
            st.subheader(f" {target_product} 競合調査レポート")
            st.markdown(report)
            
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")