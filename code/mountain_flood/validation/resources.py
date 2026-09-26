# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""计算资源占用区间的最大并发数，供验证和问题四共用。"""

def peak(intervals):
    events=sorted([(a,1) for a,b in intervals]+[(b,-1) for a,b in intervals])
    count=maximum=0
    for _,d in events:count+=d;maximum=max(maximum,count)
    return maximum
