"""Shared model/company aliases for topic, date evidence and navigation."""
import re

ALIASES = {
    'ChatGPT': ('ChatGPT',), 'GPT': ('GPT',), 'OpenAI': ('OpenAI',),
    'Claude': ('Claude', 'Anthropic'), 'Gemini': ('Gemini', 'Google Gemini'),
    'DeepSeek': ('DeepSeek', '深度求索'),
    'GLM': ('GLM', '智谱', 'Zhipu', 'Z.ai'),
    'Kimi': ('Kimi', '月之暗面', 'Moonshot'),
    'Qwen': ('Qwen', '通义千问', '千问', '通义'),
    '豆包': ('豆包', 'Doubao'),
    'ERNIE': ('ERNIE', '文心一言', '文心'),
    'Hunyuan': ('Hunyuan', '混元'),
    'MiniMax': ('MiniMax', '稀宇'), '阶跃星辰': ('StepFun', '阶跃星辰'),
    'InternLM': ('InternLM', '书生'), '百川': ('Baichuan', '百川'),
    '零一万物': ('零一万物',), '星火': ('讯飞星火', '星火'),
    'Llama': ('Llama', 'Meta Llama'), 'Grok': ('Grok', 'xAI'), 'Mistral': ('Mistral',),
    '小米MiMo': ('MiMo', 'Xiaomi MiMo', '小米MiMo', '小米大模型'),
    '盘古': ('Pangu', '盘古'), '日日新': ('SenseNova', '日日新', '商汤'),
    'LongCat': ('LongCat', '美团LongCat'), 'MiniCPM': ('MiniCPM', 'OpenBMB'),
    'InternVL': ('InternVL', 'OpenGVLab'), 'BAAI': ('BAAI', '智源'),
    'Ant Ling': ('Ant Ling', '蚂蚁百灵'), 'Wan': ('Wan', '万相'),
    'Skywork': ('Skywork', '昆仑万维'), 'Seed': ('ByteDance Seed', '字节Seed'),
}
LOOKUP = {alias.casefold(): name for name, aliases in ALIASES.items() for alias in aliases}
parts = []
for alias in sorted(LOOKUP, key=len, reverse=True):
    escaped = re.escape(alias)
    parts.append(r'(?<![A-Za-z0-9_])' + escaped + r'(?![A-Za-z_])' if alias.isascii() else escaped)
MODEL_NAMES = re.compile('|'.join(parts), re.I)


def model_labels(text):
    return list(dict.fromkeys(LOOKUP[m.group().casefold()] for m in MODEL_NAMES.finditer(text)))
