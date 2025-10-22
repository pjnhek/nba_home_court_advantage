FROM continuumio/miniconda3

WORKDIR /API_SERVER
RUN pwd

COPY environment.yml .
RUN conda env create -f environment.yml -n msds692-proj
RUN conda install -n msds692-proj fastapi[standard]

COPY . .

EXPOSE 8000

# Use uvicorn directly with increased timeouts for long-running scraping tasks
CMD ["conda", "run", "--no-capture-output", "-n", "msds692-proj", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "1800", "--timeout-graceful-shutdown", "30"]