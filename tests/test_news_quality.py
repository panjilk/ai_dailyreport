from dailyreport.topics import concrete_news


def test_vague_summary_cannot_borrow_specificity_from_headline():
    assert not concrete_news('OpenAI发布新模型', ['两场AI安全讨论如火如荼，事实与虚构难以区分。'])
    assert not concrete_news('MCP一直是个坏主意？', ['英文技术博客摘录；观点与判断属于原作者，未经独立复核。', '我对MCP的评论。'])


def test_concrete_model_and_product_updates_pass():
    assert concrete_news('千问办公升级', ['千问办公新增企业上下文功能，统一管理Agent的数据和任务权限。'])
    assert concrete_news('Muse下载情况', ['Appfigures估计，Muse在美国和加拿大上线同期的下载量超过ChatGPT早期移动版。'])
