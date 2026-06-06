from opensearchpy import OpenSearch

from app.config import settings


def get_opensearch_client() -> OpenSearch:
    auth = None
    if settings.opensearch_username and settings.opensearch_password:
        auth = (settings.opensearch_username, settings.opensearch_password)

    return OpenSearch(
        hosts=[settings.opensearch_host],
        http_auth=auth,
        use_ssl=settings.opensearch_host.startswith("https://"),
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
