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
        
        # Generic video-related and content terms to exclude
        self.video_terms = {
            'video', 'videos', 'youtube', 'channel', 'subscribe', 'subscriber',
            'like', 'comment', 'comments', 'share', 'watch', 'watching', 'watched',
            'view', 'views', 'viewer', 'viewers', 'upload', 'uploaded', 'content',
            'creator', 'creators', 'youtuber', 'thumbnail', 'description', 'playlist',
            'notification', 'bell', 'click', 'link', 'minute', 'minutes', 'second',
            'seconds', 'hour', 'hours', 'time', 'part', 'episode', 'series',
            # Generic content descriptors
            'song', 'songs', 'music', 'track', 'tracks', 'album', 'artist', 'band',
            'movie', 'movies', 'film', 'films', 'cinema', 'scene', 'scenes',
            'show', 'shows', 'tv', 'television', 'season', 'episodes',
            'clip', 'clips', 'footage', 'trailer', 'teaser', 'preview',
            'performance', 'concert', 'live', 'studio', 'official', 'unofficial',
            'version', 'remix', 'cover', 'original', 'remaster', 'edit',
            'reaction', 'review', 'analysis', 'breakdown', 'explained', 'tutorial'
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
        
        # Topic-specific terms that reveal content themes (excluding generic content terms)
        self.topic_indicators = {
            'tutorial': ['learn', 'teach', 'guide', 'howto', 'steps', 'process', 'method'],
            'entertainment': ['funny', 'hilarious', 'laugh', 'comedy', 'entertaining', 'fun'],
            'audio_quality': ['beat', 'rhythm', 'melody', 'voice', 'sound', 'audio', 'vocals'],
            'gaming': ['game', 'play', 'player', 'level', 'score', 'win', 'lose'],
            'tech': ['software', 'hardware', 'computer', 'phone', 'app', 'program', 'code'],
            'cooking': ['recipe', 'food', 'cook', 'ingredient', 'delicious', 'taste'],
            'fitness': ['workout', 'exercise', 'fitness', 'gym', 'muscle', 'health'],
            'education': ['learn', 'study', 'understand', 'knowledge', 'information']
        }
    
    def extract_meaningful_keywords(self, comments: List[str], max_keywords: int = 10, title_words: List[str] = None) -> List[Tuple[str, int]]:
        """
        Extract meaningful keywords from comments, excluding stop words, generic terms, and title words.
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
        
        # Create title words filter set
        title_filter = set()
        if title_words:
            for word in title_words:
                # Clean and filter title words
                clean_word = re.sub(r'[^a-zA-Z]', '', word.lower())
                if len(clean_word) > 3 and clean_word not in self.stop_words:
                    title_filter.add(clean_word)
        
        # Filter out stop words, video terms, title words, and short words
        meaningful_words = [
            word for word in words 
            if len(word) > 3 
            and word not in self.stop_words 
            and word not in self.video_terms
            and word not in title_filter
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
    
    def detect_controversial_topics(self, comments: List[str]) -> List[Dict[str, Any]]:
        """
        Detect controversial topics and debates in the comments.
        """
        controversial_indicators = {
            'disagreement': ['disagree', 'wrong', 'not true', 'actually', 'but', 'however', 'although'],
            'strong_opinions': ['absolutely', 'definitely', 'completely', 'totally', 'never', 'always'],
            'debate_starters': ['unpopular opinion', 'hot take', 'controversial', 'debate', 'argue'],
            'political': ['left', 'right', 'liberal', 'conservative', 'politics', 'government'],
            'personal_attacks': ['stupid', 'idiot', 'moron', 'pathetic', 'ridiculous'],
            'defensive': ['triggered', 'offended', 'sensitive', 'cope', 'mad']
        }
        
        topics = []
        controversy_scores = {}
        
        # Sample comments to avoid performance issues
        sample_size = min(len(comments), 300)
        sample_comments = comments[:sample_size]
        
        for i, comment in enumerate(sample_comments):
            comment_lower = comment.lower()
            controversy_score = 0
            indicators_found = []
            
            # Check for controversial indicators
            for category, indicators in controversial_indicators.items():
                for indicator in indicators:
                    if indicator in comment_lower:
                        controversy_score += 1
                        indicators_found.append(category)
            
            # High controversy if multiple indicators or sensitive topics
            if controversy_score >= 2 or any(cat in indicators_found for cat in ['political', 'personal_attacks']):
                topics.append({
                    'text': comment[:200] + ('...' if len(comment) > 200 else ''),
                    'score': controversy_score,
                    'categories': list(set(indicators_found)),
                    'index': i
                })
        
        # Sort by controversy score
        topics.sort(key=lambda x: x['score'], reverse=True)
        return topics[:5]  # Return top 5 controversial topics
    
    def extract_discussion_themes(self, comments: List[str], title_words: List[str] = None) -> List[Dict[str, Any]]:
        """
        Extract major discussion themes and topics from comments.
        """
        # Get meaningful keywords first
        keywords = self.extract_meaningful_keywords(comments, max_keywords=20, title_words=title_words)
        
        # Group related keywords into themes
        theme_categories = {
            'quality': ['quality', 'production', 'editing', 'cinematography', 'direction', 'acting'],
            'technical': ['audio', 'sound', 'video', 'graphics', 'resolution', 'streaming'],
            'content': ['story', 'plot', 'narrative', 'characters', 'dialogue', 'script'],
            'educational': ['learn', 'educational', 'informative', 'helpful', 'tutorial', 'explanation'],
            'entertainment': ['funny', 'entertaining', 'humor', 'comedy', 'hilarious', 'amusing'],
            'emotional': ['emotional', 'touching', 'heartwarming', 'inspiring', 'motivating', 'uplifting'],
            'comparison': ['better', 'worse', 'compared', 'similar', 'different', 'like'],
            'personal': ['experience', 'personal', 'relate', 'happened', 'remember', 'story']
        }
        
        themes = []
        keyword_dict = dict(keywords)
        
        for theme_name, theme_words in theme_categories.items():
            theme_score = 0
            found_words = []
            
            for word in theme_words:
                if word in keyword_dict:
                    theme_score += keyword_dict[word]
                    found_words.append(word)
            
            if theme_score > 3:  # Minimum threshold
                themes.append({
                    'name': theme_name,
                    'score': theme_score,
                    'keywords': found_words[:3],
                    'percentage': round((theme_score / sum(count for _, count in keywords[:10]) * 100), 1)
                })
        
        # Sort by score
        themes.sort(key=lambda x: x['score'], reverse=True)
        return themes[:4]  # Return top 4 themes
    
    def generate_enhanced_summary(self, 
                                   comments: List[Any],
                                   sentiment_data: Dict[str, Any],
                                   video_info: Dict[str, Any] = None) -> str:
        """
        Generate a comprehensive, conversational summary with deep insights.
        """
        # Extract comment texts
        comment_texts = []
        total_comments_count = len(comments)
        for c in comments:
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
        
        # Extract title words for filtering
        title_words = []
        if video_info and video_info.get('title'):
            title_words = video_info['title'].split()
        
        # Get comprehensive analysis
        emotions = self.identify_emotion_patterns(comment_texts)
        quality = self.analyze_comment_quality(comment_texts)
        keywords = self.extract_meaningful_keywords(comment_texts, max_keywords=15, title_words=title_words)
        themes = self.extract_discussion_themes(comment_texts, title_words=title_words)
        controversies = self.detect_controversial_topics(comment_texts)
        
        # Start building conversational summary
        summary_parts = []
        
        # Opening with conversational tone
        if pos_pct > 75:
            opening = f"The audience is absolutely loving this content! With {pos_pct}% positive reactions, it's clear this really resonated with viewers."
        elif pos_pct > 60:
            opening = f"This content is getting a warm reception from the audience, with {pos_pct}% positive reactions outweighing the {neg_pct}% negative ones."
        elif neg_pct > 60:
            opening = f"The comments reveal some significant criticism here, with {neg_pct}% of viewers expressing negative sentiments."
        elif abs(pos_pct - neg_pct) < 10:
            opening = f"This content has really split the audience down the middle - we're seeing {pos_pct}% positive and {neg_pct}% negative reactions, making it quite polarizing."
        else:
            opening = f"The reaction is fairly mixed across the board, with {pos_pct}% positive, {neu_pct}% neutral, and {neg_pct}% negative responses."
        
        summary_parts.append(opening)
        
        # Discuss major themes in conversation style
        if themes:
            theme_intro = "\n\nLooking at what people are actually talking about, "
            theme_descriptions = []
            
            for i, theme in enumerate(themes[:3]):
                theme_name = theme['name']
                keywords = theme['keywords']
                percentage = theme.get('percentage', 0)
                
                if theme_name == 'quality':
                    theme_descriptions.append(f"there's quite a bit of discussion around the production quality, with viewers mentioning {', '.join(keywords)}")
                elif theme_name == 'educational':
                    theme_descriptions.append(f"many people are appreciating the educational value, frequently discussing {', '.join(keywords)}")
                elif theme_name == 'entertainment':
                    theme_descriptions.append(f"the entertainment factor is a big talking point, with comments about {', '.join(keywords)}")
                elif theme_name == 'technical':
                    theme_descriptions.append(f"viewers are getting into the technical aspects, particularly {', '.join(keywords)}")
                elif theme_name == 'emotional':
                    theme_descriptions.append(f"there's a strong emotional response, with people talking about {', '.join(keywords)}")
                elif theme_name == 'comparison':
                    theme_descriptions.append(f"viewers are making comparisons, often mentioning {', '.join(keywords)}")
                else:
                    theme_descriptions.append(f"the {theme_name} aspect is generating discussion around {', '.join(keywords)}")
            
            if theme_descriptions:
                if len(theme_descriptions) == 1:
                    summary_parts.append(theme_intro + theme_descriptions[0] + ".")
                else:
                    summary_parts.append(theme_intro + ", ".join(theme_descriptions[:-1]) + f", and {theme_descriptions[-1]}.")
        
        # Analyze emotional undercurrents
        emotion_insights = []
        top_emotions = sorted([(e, v) for e, v in emotions.items() if v > 8], key=lambda x: x[1], reverse=True)
        
        if top_emotions:
            for emotion, percentage in top_emotions[:3]:
                if emotion == 'enthusiasm' and percentage > 15:
                    emotion_insights.append(f"genuine enthusiasm ({percentage}% of comments)")
                elif emotion == 'frustration' and percentage > 12:
                    emotion_insights.append(f"notable frustration ({percentage}% of comments)")
                elif emotion == 'gratitude' and percentage > 15:
                    emotion_insights.append(f"heartfelt gratitude ({percentage}% of comments)")
                elif emotion == 'curiosity' and percentage > 15:
                    emotion_insights.append(f"curious engagement ({percentage}% asking questions)")
                elif emotion == 'humor' and percentage > 12:
                    emotion_insights.append(f"humor and amusement ({percentage}% of comments)")
                elif emotion == 'recommendation' and percentage > 8:
                    emotion_insights.append(f"strong recommendations to others ({percentage}% of comments)")
            
            if emotion_insights:
                summary_parts.append(f"\n\nEmotionally, the comment section shows {', '.join(emotion_insights[:-1])}" + 
                                    (f", and {emotion_insights[-1]}" if len(emotion_insights) > 1 else emotion_insights[0]) + ".")
        
        # Comment quality and engagement patterns
        engagement_notes = []
        if quality['detailed_percentage'] > 35:
            engagement_notes.append(f"a high number of detailed, thoughtful responses ({quality['detailed_percentage']}% are longer than 100 characters)")
        elif quality['detailed_percentage'] < 15:
            engagement_notes.append("mostly quick reactions rather than detailed commentary")
        
        if quality['engaging_percentage'] > 25:
            engagement_notes.append(f"active discussion and debate ({quality['engaging_percentage']}% include questions or strong opinions)")
        
        if engagement_notes:
            summary_parts.append(f"\n\nThe comment section itself shows {' and '.join(engagement_notes)}.")
        
        # Controversial topics and debates
        if controversies:
            controversy_intro = "\n\n🔥 There are some heated discussions brewing in the comments. "
            controversy_details = []
            
            for controversy in controversies[:2]:
                categories = controversy['categories']
                if 'disagreement' in categories:
                    controversy_details.append("viewers are debating and disagreeing with each other")
                elif 'political' in categories:
                    controversy_details.append("some political undertones are sparking debate")
                elif 'personal_attacks' in categories:
                    controversy_details.append("tensions are running high with some heated exchanges")
                elif 'strong_opinions' in categories:
                    controversy_details.append("people are expressing very strong, absolute opinions")
            
            if controversy_details:
                summary_parts.append(controversy_intro + "We're seeing " + ", ".join(controversy_details[:2]) + 
                                    (f", and {controversy_details[2]}" if len(controversy_details) > 2 else "") + 
                                    f". About {len(controversies)} comments are particularly divisive.")
        
        # Confidence and analysis notes
        if confidence < 0.6:
            summary_parts.append(f"\n\n📊 Analysis note: The relatively lower confidence score ({confidence*100:.1f}%) suggests that many comments contain nuanced, sarcastic, or ambiguous language that makes sentiment harder to pin down - which often happens with more sophisticated or ironic commentary.")
        elif confidence > 0.85:
            summary_parts.append(f"\n\n📊 Analysis note: The high confidence score ({confidence*100:.1f}%) indicates that viewers are expressing their feelings quite clearly and directly, without much ambiguity or sarcasm.")
        
        # Final insights based on patterns
        if pos_pct > 80 and emotions.get('gratitude', 0) > 20:
            summary_parts.append("\n\n💡 This appears to be the kind of content that genuinely helps or inspires people - the combination of high positivity and gratitude suggests real value delivery.")
        elif neg_pct > 50 and emotions.get('frustration', 0) > 25:
            summary_parts.append("\n\n💡 There seems to be a disconnect between what viewers expected and what they got, leading to disappointment and frustration.")
        elif abs(pos_pct - neg_pct) < 5 and controversies:
            summary_parts.append("\n\n💡 This content has hit a nerve and created a real divide in the audience - it's the kind of topic that people have strong opinions about either way.")
        elif emotions.get('recommendation', 0) > 15:
            summary_parts.append("\n\n💡 Viewers are actively recommending this to others, which suggests it has strong word-of-mouth potential.")
        
        return ''.join(summary_parts)


def get_enhanced_summary(comments: List[Any], 
                         sentiment_data: Dict[str, Any],
                         video_info: Dict[str, Any] = None) -> str:
    """
    Convenience function to generate enhanced summary with video title filtering.
    """
    enhancer = SummaryEnhancer()
    return enhancer.generate_enhanced_summary(comments, sentiment_data, video_info)
