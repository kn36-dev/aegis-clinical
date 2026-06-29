How to use OTel in the project?

Install with:
```
uv add opentelemetry-distro opentelemetry-exporter-otlp opentelemetry-instrumentation-langchain
```

Initialize before LangGraph starts:
```
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# Automatically hooks into all LangChain runnables, CrewAI tools, and LangGraph nodes
LangchainInstrumentor().instrument()
```

<!-- What's above is old -->
Use these instead so it's not tied to LangChain
uv add \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-fastapi