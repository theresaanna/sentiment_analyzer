"""
Enhanced summary generator for sentiment analysis.
Provides meaningful, dataset-specific insights avoiding generic terms.
"""

import re
from typing import Dict, List, Any, Tuple
from collections import Counter
import string


class SummaryEnhancer:
    """Generate enhanced summaries with unique insights from comment data."""
    
    def __init__(self):
        # Common stop words to exclude (expanded list)
        self.stop_words = {
            # Articles, pronouns, prepositions
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'around',
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you',
            'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
            'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them',
            'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this',
            'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
            'will', 'would', 'should', 'could', 'ought', 'may', 'might', 'must',
            'can', 'cannot', 'shall', 'as', 'so', 'than', 'too', 'very', 's', 't',
            'd', 'll', 'm', 've', 're', 'just', 'here', 'there', 'now', 'then',
            'once', 'all', 'much', 'many', 'some', 'few', 'more', 'most', 'other',
            'such', 'only', 'own', 'same', 'well', 'back', 'even', 'still', 'also',
            'get', 'got', 'getting', 'like', 'really', 'actually', 'basically',
            'literally', 'thing', 'things', 'stuff', 'way', 'yeah', 'yes', 'no',
            'not', 'dont', 'didn', 'doesn', 'wasn', 'weren', 'isn', 'aren',
            'won', 'wouldn', 'couldn', 'shouldn', 'mightn', 'mustn', 'needn',
            'hasn', 'haven', 'hadn', 'u', 'ur', 'r', 'n', 'b', 'c', 'already'
        }
        
        # Generic video-related terms to exclude
        self.video_terms = {
            'video', 'videos', 'youtube', 'channel', 'subscribe', 'subscriber',
            'like', 'comment', 'comments', 'share', 'watch', 'watching', 'watched',
            'view', 'views', 'viewer', 'viewers', 'upload', 'uploaded', 'content',
            'creator', 'creators', 'youtuber', 'thumbnail', 'description', 'playlist',
            'notification', 'bell', 'click', 'link', 'minute', 'minutes', 'second',
            'seconds', 'hour', 'hours', 'time', 'part', 'episode', 'series'
        }
        
        # Sentiment-specific meaningful words to look for
        self.positive_indicators = {
            'excellent', 'amazing', 'wonderful', 'fantastic', 'brilliant', 'awesome',
            'incredible', 'outstanding', 'perfect', 'beautiful', 'masterpiece',
            'genius', 'inspiring', 'impressive', 'phenomenal', 'exceptional',
            'love', 'loved', 'loving', 'enjoy', 'enjoyed', 'enjoying', 'appreciate',
            'grateful', 'thankful', 'blessed', 'happy', 'excited', 'thrilled',
            'delighted', 'satisfied', 'proud', 'recommend', 'helpful', 'useful',
            'informative', 'educational', 'insightful', 'valuable', 'important',
            'professional', 'quality', 'clear', 'detailed', 'thorough', 'comprehensive'
        }
        
        self.negative_indicators = {
            'terrible', 'horrible', 'awful', 'disgusting', 'disappointing', 'waste',
            'useless', 'pointless', 'boring', 'confusing', 'misleading', 'clickbait',
            'fake', 'scam', 'stupid', 'dumb', 'ridiculous', 'annoying', 'frustrating',
            'hate', 'hated', 'dislike', 'disappointed', 'regret', 'unfortunate',
            'poor', 'bad', 'worse', 'worst', 'fail', 'failed', 'failure', 'problem',
            'issue', 'wrong', 'incorrect', 'inaccurate', 'unclear', 'difficult',
            'complicated', 'trash', 'garbage', 'cringe', 'pathetic', 'lame'
        }
        
        # Topic-specific terms that reveal content themes
        self.topic_indicators = {
            'tutorial': ['learn', 'teach', 'explain', 'guide', 'howto', 'steps', 'process'],
            'entertainment': ['funny', 'hilarious', 'laugh', 'comedy', 'entertaining', 'fun'],
            'music': ['song', 'music', 'beat', 'rhythm', 'melody', 'voice', 'sound'],
            'gaming': ['game', 'play', 'player', 'level', 'score', 'win', 'lose'],
            'tech': ['software', 'hardware', 'computer', 'phone', 'app', 'program', 'code'],
            'cooking': ['recipe', 'food', 'cook', 'ingredient', 'delicious', 'taste'],
            'fitness': ['workout', 'exercise', 'fitness', 'gym', 'muscle', 'health'],
            'education': ['learn', 'study', 'understand', 'knowledge', 'information', 'explain']
        }
    
    def extract_meaningful_keywords(self, comments: List[str], max_keywords: int = 10) -> List[Tuple[str, int]]:
        """
        Extract meaningful keywords from comments, excluding stop words and generic terms.
        Returns list of (keyword, frequency) tuples.
        """
        # Limit comments for keyword extraction to avoid performance issues
        comments_for_keywords = comments[:500] if len(comments) > 500 else comments
        # Combine comments into one text
        all_text = ' '.join(comments_for_keywords).lower()
        
        # Remove URLs, mentions, and special characters
        all_text = re.sub(r'http\S+', '', all_text)
        all_text = re.sub(r'@\S+', '', all_text)
        all_text = re.sub(r'#\S+', '', all_text)
        
        # Extract words (keeping only alphabetic characters)
        words = re.findall(r'\b[a-z]+\b', all_text)
        
        # Filter out stop words, video terms, and short words
        meaningful_words = [
            word for word in words 
            if len(word) > 3 
            and word not in self.stop_words 
            and word not in self.video_terms
        ]
        
        # Count word frequencies
        word_freq = Counter(meaningful_words)
        
        # Get most common words
        return word_freq.most_common(max_keywords)
    
    def identify_emotion_patterns(self, comments: List[str]) -> Dict[str, float]:
        """
        Identify emotional patterns in comments beyond basic sentiment.
        Returns percentages of different emotional expressions.
        """
        emotions = {
            'enthusiasm': 0,
            'frustration': 0,
            'curiosity': 0,
            'gratitude': 0,
            'criticism': 0,
            'humor': 0,
            'confusion': 0,
            'recommendation': 0
        }
        
        # Define patterns for each emotion
        patterns = {
            'enthusiasm': ['excited', 'cant wait', 'amazing', 'awesome', 'love this', 'best ever', '!!!', 'wow'],
            'frustration': ['frustrated', 'annoying', 'waste', 'disappointed', 'expected better', 'come on'],
            'curiosity': ['wondering', 'curious', 'question', 'how', 'why', 'what if', 'anyone know', '?'],
            'gratitude': ['thank', 'thanks', 'grateful', 'appreciate', 'helped me', 'useful'],
            'criticism': ['should have', 'could be better', 'needs', 'lacking', 'missing', 'poor'],
            'humor': ['lol', 'haha', 'funny', 'hilarious', 'joke', 'laughing', 'comedy', '😂', '🤣'],
            'confusion': ['confused', 'dont understand', 'unclear', 'what', 'lost', 'complicated'],
            'recommendation': ['recommend', 'must watch', 'check out', 'worth', 'dont miss', 'everyone should']
        }
        
        total_comments = len(comments)
        if total_comments == 0:
            return emotions
        
        # Sample comments if too many for performance
        comments_to_analyze = comments[:1000] if len(comments) > 1000 else comments
        
        for comment in comments_to_analyze:
            comment_lower = comment.lower()
            for emotion, keywords in patterns.items():
                if any(kw in comment_lower for kw in keywords):
                    emotions[emotion] += 1
        
        # Convert to percentages
        for emotion in emotions:
            emotions[emotion] = round((emotions[emotion] / total_comments) * 100, 1)
        
        return emotions
    
    def analyze_comment_quality(self, comments: List[str]) -> Dict[str, Any]:
        """
        Analyze the quality and depth of comments.
        """
        total = len(comments)
        if total == 0:
            return {'avg_length': 0, 'detailed_percentage': 0, 'engaging_percentage': 0}
        
        lengths = [len(c) for c in comments]
        avg_length = sum(lengths) / total
        
        # Comments over 100 chars are considered detailed
        detailed = sum(1 for l in lengths if l > 100)
        detailed_pct = round((detailed / total) * 100, 1)
        
        # Comments with questions or discussions are engaging
        engaging = sum(1 for c in comments if '?' in c or any(
            phrase in c.lower() for phrase in ['agree', 'disagree', 'think', 'opinion', 'believe']
        ))
        engaging_pct = round((engaging / total) * 100, 1)
        
        return {
            'avg_length': round(avg_length),
            'detailed_percentage': detailed_pct,
            'engaging_percentage': engaging_pct
        }
    
    def generate_enhanced_summary(self, 
                                   comments: List[Any],
                                   sentiment_data: Dict[str, Any],
                                   video_info: Dict[str, Any] = None) -> str:
        """
        Generate an enhanced summary with unique insights.
        """
        # Extract comment texts
        comment_texts = []
        # Use all comments for summary, but limit for keyword extraction
        total_comments_count = len(comments)
        for c in comments:  # Process all comments
            if isinstance(c, dict):
                text = c.get('text', '')
            else:
                text = str(c)
            if text:
                comment_texts.append(text)
        
        if not comment_texts:
            return "Unable to generate summary due to insufficient comment data."
        
        # Get sentiment distribution
        dist = sentiment_data.get('sentiment_distribution') or sentiment_data.get('distribution') or {}
        total = sentiment_data.get('total_analyzed', 0)
        confidence = sentiment_data.get('average_confidence', 0)
        
        if total == 0:
            return "No comments analyzed."
        
        # Calculate percentages
        pos_pct = round((dist.get('positive', 0) / total * 100), 1)
        neu_pct = round((dist.get('neutral', 0) / total * 100), 1)
        neg_pct = round((dist.get('negative', 0) / total * 100), 1)
        
        # Determine overall tone
        if pos_pct > 70:
            tone = "overwhelmingly positive"
        elif pos_pct > 50:
            tone = "predominantly positive"
        elif neg_pct > 60:
            tone = "largely critical"
        elif neg_pct > 40:
            tone = "notably critical"
        elif abs(pos_pct - neg_pct) < 10:
            tone = "highly polarized"
        else:
            tone = "mixed"
        
        # Start building summary
        summary_parts = []
        
        # Opening statement
        summary_parts.append(
            f"Audience reaction is {tone} ({pos_pct}% positive, {neu_pct}% neutral, {neg_pct}% negative)."
        )
        
        # Extract meaningful keywords
        keywords = self.extract_meaningful_keywords(comment_texts, max_keywords=8)
        if keywords and len(keywords) >= 3:
            # Group keywords by sentiment if possible
            keyword_list = [word for word, _ in keywords[:5]]
            
            # Check which keywords appear more in positive vs negative contexts
            pos_keywords = []
            neg_keywords = []
            neutral_keywords = []
            
            for keyword in keyword_list:
                pos_count = sum(1 for c in comment_texts[:100] 
                               if keyword in c.lower() and any(
                                   ind in c.lower() for ind in self.positive_indicators))
                neg_count = sum(1 for c in comment_texts[:100]
                               if keyword in c.lower() and any(
                                   ind in c.lower() for ind in self.negative_indicators))
                
                if pos_count > neg_count * 1.5:
                    pos_keywords.append(keyword)
                elif neg_count > pos_count * 1.5:
                    neg_keywords.append(keyword)
                else:
                    neutral_keywords.append(keyword)
            
            # Add keyword insights
            if pos_keywords:
                summary_parts.append(
                    f"Positive feedback centers on: {', '.join(pos_keywords[:3])}."
                )
            if neg_keywords:
                summary_parts.append(
                    f"Concerns mentioned include: {', '.join(neg_keywords[:3])}."
                )
            if not pos_keywords and not neg_keywords and neutral_keywords:
                summary_parts.append(
                    f"Key discussion topics: {', '.join(neutral_keywords[:4])}."
                )
        
        # Analyze emotional patterns
        emotions = self.identify_emotion_patterns(comment_texts)
        top_emotions = sorted(
            [(e, v) for e, v in emotions.items() if v > 10],
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        if top_emotions:
            emotion_insights = []
            for emotion, percentage in top_emotions:
                if emotion == 'enthusiasm' and percentage > 20:
                    emotion_insights.append(f"{percentage}% express strong enthusiasm")
                elif emotion == 'frustration' and percentage > 15:
                    emotion_insights.append(f"{percentage}% voice frustration")
                elif emotion == 'gratitude' and percentage > 15:
                    emotion_insights.append(f"{percentage}% express gratitude")
                elif emotion == 'curiosity' and percentage > 20:
                    emotion_insights.append(f"{percentage}% have questions or show curiosity")
                elif emotion == 'humor' and percentage > 15:
                    emotion_insights.append(f"{percentage}% found it humorous")
                elif emotion == 'recommendation' and percentage > 10:
                    emotion_insights.append(f"{percentage}% recommend to others")
            
            if emotion_insights:
                summary_parts.append(
                    f"Notable patterns: {' and '.join(emotion_insights)}."
                )
        
        # Analyze comment quality
        quality = self.analyze_comment_quality(comment_texts)
        quality_insights = []
        
        if quality['detailed_percentage'] > 40:
            quality_insights.append("viewers are writing detailed responses")
        elif quality['detailed_percentage'] < 20:
            quality_insights.append("most comments are brief reactions")
        
        if quality['engaging_percentage'] > 30:
            quality_insights.append("high discussion engagement")
        
        if quality_insights:
            summary_parts.append(
                f"Comment characteristics: {' with '.join(quality_insights)}."
            )
        
        # Add confidence note if relevant
        if confidence < 0.6:
            summary_parts.append(
                "Note: Lower confidence scores suggest nuanced or sarcastic expressions."
            )
        elif confidence > 0.85:
            summary_parts.append(
                "High confidence indicates clear, unambiguous sentiment expressions."
            )
        
        # Identify unique aspects
        if pos_pct > 80 and emotions.get('gratitude', 0) > 20:
            summary_parts.append(
                "This content has genuinely helped or inspired many viewers."
            )
        elif neg_pct > 50 and emotions.get('frustration', 0) > 30:
            summary_parts.append(
                "Viewers expected something different from this content."
            )
        elif abs(pos_pct - neg_pct) < 5:
            summary_parts.append(
                "This content is divisive, splitting the audience almost evenly."
            )
        
        return ' '.join(summary_parts)


def get_enhanced_summary(comments: List[Any], 
                         sentiment_data: Dict[str, Any],
                         video_info: Dict[str, Any] = None) -> str:
    """
    Convenience function to generate enhanced summary.
    """
    enhancer = SummaryEnhancer()
    return enhancer.generate_enhanced_summary(comments, sentiment_data, video_info)