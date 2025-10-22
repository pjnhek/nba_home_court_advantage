FROM continuumio/anaconda3

WORKDIR /STREAMLIT
RUN pwd

COPY environment.yml .
RUN conda env create -f environment.yml -n msds692-proj

COPY *.py .

EXPOSE 8501

CMD ["conda", "run", "--no-capture-output", "-n", "msds692-proj", "streamlit", "run", "interactive_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=true", "--server.enableXsrfProtection=false"]