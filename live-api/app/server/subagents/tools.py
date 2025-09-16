from langchain_tavily import TavilySearch

medication_lookup_tool = TavilySearch(
    max_results=3,
    topic="medical",
    include_answer="advanced",
    # include_raw_content=False,
    include_images=True,
    include_image_descriptions=True,
    search_depth="advanced",
    # time_range="day",
    # start_date=None,
    # end_date=None,
    include_domains="https://www.nhs.uk/health-a-to-z/",
    country="uk",
    # exclude_domains=None
)
