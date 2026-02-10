from intel.types import IntelDepth

class DepthRecommender:
    """Recommend intelligence gathering depth based on query complexity."""
    
    def recommend(self, query: str) -> IntelDepth:
        """Analyze query and recommend a depth.
        
        Heuristics:
        - "DEEP": If query asks for deep analysis, full content, specific details requiring scraping.
        - "STANDARD": Default for most research queries.
        - "SHALLOW": Simple fact lookups, weather, price checks.
        """
        q_lower = query.lower()
        
        deep_triggers = ["analyze", "report", "comprehensive", "full text", "scrape", "deep"]
        shallow_triggers = ["price", "current", "weather", "who is", "define", "simple"]
        
        if any(t in q_lower for t in deep_triggers):
            return IntelDepth.DEEP
            
        if any(t in q_lower for t in shallow_triggers):
            return IntelDepth.SHALLOW
            
        return IntelDepth.STANDARD
        
def get_depth_recommender() -> DepthRecommender:
    return DepthRecommender()
