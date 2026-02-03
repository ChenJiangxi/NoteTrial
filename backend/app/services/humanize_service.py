"""
NoteTrial Backend - AI检测规避服务
降低内容的"AI味"，使其更像真人创作
"""
import re
import random
from typing import List, Tuple, Dict


class HumanizeService:
    """
    内容人性化服务
    
    核心策略：
    1. 口语化改写：将书面语转为口语
    2. 个性化注入：添加个人经历、情感色彩
    3. 不完美模拟：适当添加小瑕疵
    4. 风格多样化：避免固定的写作模式
    """
    
    # 典型的AI用语（需要避免）
    AI_PATTERNS = [
        # 过于正式的开头
        r"^作为一个",
        r"^首先，",
        r"^接下来，",
        r"^总的来说",
        r"^综上所述",
        r"^值得注意的是",
        
        # 过于工整的结构
        r"第一[，,].*第二[，,].*第三",
        r"首先.*其次.*最后",
        r"一方面.*另一方面",
        
        # 典型AI措辞
        r"这个问题",
        r"需要指出",
        r"不难发现",
        r"显而易见",
        r"毋庸置疑",
        r"众所周知",
        r"事实上",
        r"实际上，",
        r"总而言之",
        r"换句话说",
    ]
    
    # 口语化替换词典
    FORMAL_TO_CASUAL = {
        "首先": ["先说", "第一个要说的是", "emmm先聊聊"],
        "其次": ["然后", "还有就是", "另外"],
        "最后": ["最后最后", "还有一点", "差点忘了"],
        "因此": ["所以", "这样一来", "那"],
        "但是": ["但", "不过", "话说回来"],
        "然而": ["但是吧", "结果呢", "可是"],
        "非常": ["超级", "真的很", "太", "巨"],
        "一些": ["几个", "一点点", "些"],
        "很多": ["超多", "一堆", "好多"],
        "需要": ["得", "要"],
        "可以": ["能", "可"],
        "或者": ["或", "要不"],
        "例如": ["比如", "像", "就像"],
        "因为": ["因为吧", "主要是", "毕竟"],
        "所以": ["所以啊", "这不就", "于是"],
        "而且": ["还", "而且吧", "加上"],
        "虽然": ["虽然吧", "虽说", "虽然是"],
        "如果": ["要是", "假如", "万一"],
        "应该": ["估计", "大概", "应该是"],
        "建议": ["推荐", "安利", "觉得"],
        "购买": ["买", "入手", "冲"],
        "非常好": ["绝了", "太香了", "爱了"],
        "推荐": ["安利", "墙裂推荐", "必入"],
        "喜欢": ["爱了", "上头", "入坑"],
        "便宜": ["划算", "性价比高", "白菜价"],
        "昂贵": ["有点肉疼", "小贵", "破费"],
    }
    
    # 小红书常用口头禅
    XHS_PHRASES = [
        "姐妹们！",
        "家人们谁懂啊",
        "救命",
        "绝绝子",
        "一整个爱住",
        "真的会谢",
        "笑死",
        "哭了",
        "啊啊啊",
        "姐妹冲！",
        "这也太绝了",
        "爱了爱了",
        "必须安利",
        "谁懂",
        "绷不住了",
        "我直接好家伙",
        "DNA动了",
        "格局打开",
        "破防了",
    ]
    
    # 个人化表达模板
    PERSONAL_TEMPLATES = [
        "说真的，我{action}之后感觉{result}",
        "一开始我也{doubt}，但{turn}",
        "作为一个{identity}，我觉得{opinion}",
        "用了{time}，真心觉得{conclusion}",
        "之前一直{past}，直到{change}",
        "我朋友推荐的，试了一下{reaction}",
        "踩了好多雷才发现这个{discovery}",
    ]
    
    # 不完美元素（适度使用）
    IMPERFECTIONS = [
        "（懒得p图直接上原图）",
        "（图片有点糊见谅）",
        "（背景乱请忽略哈）",
        "ps: 之前照片没找到用的旧图",
        "emmm可能表达不太清楚",
        "（写得有点乱，将就看吧）",
    ]
    
    def __init__(self):
        self.style_counter = 0  # 用于轮换风格
    
    def detect_ai_patterns(self, text: str) -> List[Tuple[str, str]]:
        """
        检测文本中的AI痕迹
        
        Returns:
            List of (pattern, matched_text)
        """
        detected = []
        
        for pattern in self.AI_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    detected.append((pattern, match if match else pattern))
        
        return detected
    
    def replace_formal_words(self, text: str) -> str:
        """将正式用语替换为口语"""
        result = text
        
        for formal, casuals in self.FORMAL_TO_CASUAL.items():
            if formal in result:
                # 随机选择一个口语替换
                casual = random.choice(casuals)
                result = result.replace(formal, casual, 1)  # 只替换一次
        
        return result
    
    def add_emotion_words(self, text: str) -> str:
        """添加情感词"""
        # 在句末随机添加语气词
        sentences = re.split(r'([。！？])', text)
        
        result_parts = []
        for i, part in enumerate(sentences):
            if part in '。！？':
                # 20%概率添加语气词
                if random.random() < 0.2:
                    emotion = random.choice(['～', '！', '~', '哈哈', '嘻嘻'])
                    result_parts.append(part)
                    result_parts.append(emotion)
                else:
                    result_parts.append(part)
            else:
                result_parts.append(part)
        
        return ''.join(result_parts)
    
    def add_xhs_flavor(self, text: str, intensity: str = "medium") -> str:
        """
        添加小红书风味
        
        Args:
            text: 原文
            intensity: low/medium/high 强度
        """
        result = text
        
        # 根据强度决定添加多少元素
        phrase_prob = {"low": 0.1, "medium": 0.2, "high": 0.3}[intensity]
        
        # 开头添加小红书口头禅
        if random.random() < phrase_prob:
            opener = random.choice(self.XHS_PHRASES[:5])  # 使用较温和的开头
            result = opener + " " + result
        
        # 在某些位置插入表情符号
        emoji_candidates = ['✨', '💕', '🔥', '👍', '💗', '🌟', '😍', '❤️']
        lines = result.split('\n')
        for i in range(len(lines)):
            if random.random() < phrase_prob and len(lines[i]) > 10:
                emoji = random.choice(emoji_candidates)
                # 在行末或行中插入
                if random.random() < 0.5:
                    lines[i] = lines[i] + emoji
                else:
                    mid = len(lines[i]) // 2
                    lines[i] = lines[i][:mid] + emoji + lines[i][mid:]
        
        return '\n'.join(lines)
    
    def humanize_title(self, title: str) -> str:
        """人性化标题"""
        result = title
        
        # 替换正式用语
        result = self.replace_formal_words(result)
        
        # 小红书标题技巧：
        # 1. 添加emoji
        if random.random() < 0.5:
            emoji = random.choice(['🔥', '✨', '💕', '❗', '‼️', '⭐'])
            result = result + emoji
        
        # 2. 使用感叹号或省略号结尾
        if not result.endswith(('！', '!', '？', '?', '…', '~')):
            if random.random() < 0.4:
                result = result + random.choice(['！', '！！', '？', '...'])
        
        return result
    
    def humanize_body(self, body: str, style: str = "casual") -> str:
        """
        人性化正文
        
        Args:
            body: 原文
            style: casual/emotional/storytelling 风格
        """
        result = body
        
        # 1. 基础口语化
        result = self.replace_formal_words(result)
        
        # 2. 检测并处理AI痕迹
        ai_detected = self.detect_ai_patterns(result)
        for pattern, matched in ai_detected:
            # 尝试移除或替换
            result = re.sub(pattern, '', result, count=1)
        
        # 3. 根据风格处理
        if style == "casual":
            result = self.add_emotion_words(result)
        elif style == "emotional":
            result = self.add_xhs_flavor(result, "medium")
        elif style == "storytelling":
            # 添加故事元素
            result = self.add_xhs_flavor(result, "low")
        
        # 4. 分段优化（避免太长的段落）
        paragraphs = result.split('\n\n')
        optimized = []
        for p in paragraphs:
            if len(p) > 200:
                # 尝试在中间断句
                mid = len(p) // 2
                break_point = p.rfind('。', 0, mid)
                if break_point > 50:
                    p = p[:break_point+1] + '\n\n' + p[break_point+1:]
            optimized.append(p)
        
        return '\n\n'.join(optimized)
    
    def generate_prompt_enhancement(self) -> str:
        """
        生成用于提示词的人性化指导
        
        用于在内容生成时就避免AI味
        """
        self.style_counter += 1
        style_index = self.style_counter % 4
        
        base_rules = """
写作风格要求（降低AI检测）：
1. 不要使用"首先、其次、最后"这样的结构
2. 不要使用"值得注意的是"、"需要指出"等书面语
3. 多用口语词：比如、然后、还有、其实、真的
4. 句子长短错落，不要每句都差不多长
5. 可以有不完整的句子或省略
6. 适当使用emoji表情，但不要过多
7. 写得像在和朋友聊天分享经验
"""
        
        style_variations = [
            "\n本次采用「闺蜜聊天」风格：像在跟好朋友分享，可以有吐槽和小情绪",
            "\n本次采用「经验分享」风格：像是踩过坑后的真心推荐，带点过来人的语气",
            "\n本次采用「种草日记」风格：发现宝藏的惊喜感，真诚但不夸张",
            "\n本次采用「实测报告」风格：客观但带个人体验，像是买家秀+使用心得",
        ]
        
        return base_rules + style_variations[style_index]
    
    def score_humanness(self, text: str) -> Dict:
        """
        评估文本的人性化程度
        
        Returns:
            {
                'score': 0-100,
                'issues': List[str],
                'ai_patterns_found': int
            }
        """
        score = 100
        issues = []
        
        # 1. 检测AI模式
        ai_patterns = self.detect_ai_patterns(text)
        ai_count = len(ai_patterns)
        score -= ai_count * 10
        if ai_count > 0:
            issues.append(f"检测到{ai_count}个AI典型用语")
        
        # 2. 检查句子长度变化
        sentences = re.split(r'[。！？]', text)
        lengths = [len(s.strip()) for s in sentences if s.strip()]
        if lengths:
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            if variance < 100:  # 句子长度太一致
                score -= 10
                issues.append("句子长度过于一致，缺乏变化")
        
        # 3. 检查是否有emoji
        emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', text))
        if emoji_count == 0:
            score -= 5
            issues.append("缺少emoji，可适当添加")
        elif emoji_count > 10:
            score -= 5
            issues.append("emoji过多，建议减少")
        
        # 4. 检查是否有口语词
        casual_words = ['其实', '然后', '真的', '超级', '太', '感觉', '觉得', '好像']
        casual_count = sum(1 for w in casual_words if w in text)
        if casual_count < 2:
            score -= 10
            issues.append("口语化程度不够")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'ai_patterns_found': ai_count
        }


# 便捷函数
_humanizer = HumanizeService()

def humanize_content(title: str, body: str) -> Tuple[str, str]:
    """便捷函数：一键人性化内容"""
    new_title = _humanizer.humanize_title(title)
    new_body = _humanizer.humanize_body(body)
    return new_title, new_body

def get_humanize_prompt() -> str:
    """获取人性化提示词"""
    return _humanizer.generate_prompt_enhancement()

def check_humanness(text: str) -> Dict:
    """检查文本人性化程度"""
    return _humanizer.score_humanness(text)
