from dailyreport.topics import playback_priority

def test_lfm_release_precedes_qwen_product():
    release = {'title': 'Liquid AI 发布 LFM2.5 本地推理模型', 'category': '模型发布'}
    product = {'title': '阿里千问 Go 开放个人智能体体验申请', 'category': '产品应用'}
    assert playback_priority(release) < playback_priority(product)
