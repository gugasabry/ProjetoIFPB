# Bibliotecas utilizadas
import cv2
from PIL import Image
import os
import requests
import io
import gtts
from playsound import playsound
from pydub import AudioSegment
import google.generativeai as genai
from dotenv import load_dotenv
from langdetect import detect
from deep_translator import GoogleTranslator
import speech_recognition as sr
import sounddevice
'''from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from openai import OpenAI
from langchain.schema import Document
from langchain_community.callbacks.openai_info import OpenAICallbackHandler'''

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria um reconhecedor de fala
recognizer = sr.Recognizer()

# Configurações da API do Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Chave da API carregada do ambiente
genai.configure(api_key=GEMINI_API_KEY)

#os.environ["OPENAI_API_KEY"] = "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"

texto_prompt = "Extraia o texto contido nesta imagem! Não precisa dizer nada além disso, apenas enviar o texto sem nenhuma mensagem a mais!"

documentos = []


def extrai_texto_da_imagem(image_path):
    try:
        # Carregue a imagem
        img = Image.open(image_path)

        # Converta a imagem para bytes (formato esperado pela API Gemini)
        with io.BytesIO() as output:
            img.save(output, format="JPEG")  # Ou PNG, dependendo da imagem
            image_bytes = output.getvalue()

        # Carregue o modelo Gemini Vision (gemini-pro-vision)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Construa o prompt (incluindo a imagem)
        prompt = texto_prompt
        image_data = {"mime_type": "image/jpeg", "data": image_bytes}  # Ajuste o tipo MIME se necessário

        # Envie a requisição ao modelo
        requisicao = model.generate_content([prompt, image_data])

        # Obtenha o texto da resposta
        texto = requisicao.text

        documentos.append(texto)

        return texto.strip()

    except Exception as e:
        print(f"Erro ao processar a imagem: {e}")
        return None


def capturar_imagem():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return frame
    else:
        raise Exception("Erro ao capturar imagem")


def carregar_imagem(caminho_imagem):
    return Image.open(caminho_imagem)


def falar_mensagem_inicial():
    mensagem = "Só um instante, a leitura está sendo processada!"
    tts = gtts.gTTS(mensagem, lang="pt-br")
    tts.save("temp.mp3")
    audio = AudioSegment.from_mp3("temp.mp3")
    audio_acelerado = audio.speedup(playback_speed=1.5)
    audio_acelerado.export("temp1.mp3", format="mp3")
    playsound("temp1.mp3")
    os.remove("temp.mp3")
    os.remove("temp1.mp3")


def falar_texto(texto):
    arquivo = open("texto.txt", "w")
    arquivo.write(texto)
    arquivo.close()
    tts = gtts.gTTS(texto, lang="pt-br")
    tts.save("temp.mp3")
    audio = AudioSegment.from_mp3("temp.mp3")
    audio_acelerado = audio.speedup(playback_speed=1.5)
    audio_acelerado.export("temp1.mp3", format="mp3")
    playsound("temp1.mp3")
    os.remove("temp.mp3")
    os.remove("temp1.mp3")


def responder_pergunta(pergunta, texto):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"Pergunta: {pergunta}\nTexto: {texto}"
    resposta = model.generate_content([prompt])
    return resposta.text


def fazer_perguntas():

    conteudo = "".join(documentos)

    while True:
        # Usa o microfone como fonte de áudio
        with sr.Microphone() as source:
            print("Você tem dúvidas?")
            recognizer.adjust_for_ambient_noise(source)  # Ajusta para o ruído ambiente
            audio = recognizer.listen(source)  # Escuta o que foi falado

        try:
            # Reconhece a fala usando o Google Web Speech API (configurado para português do Brasil)
            pergunta = recognizer.recognize_google(audio, language="pt-BR")
            resposta = responder_pergunta(pergunta, conteudo)
            print(f"Pergunta: {pergunta}\nResposta: {resposta}\n")

        except sr.UnknownValueError:
            print("Não consegui entender o áudio.")

        except sr.RequestError:
            print("Não foi possível acessar o serviço de reconhecimento de fala.")



def traduz(texto, idioma):
    if idioma == "pt":
        return texto

    elif idioma == "en":
        tradutor = GoogleTranslator(source='en', target='pt')
        traducao = tradutor.translate(texto)
        return traducao

    elif idioma == "es":
        tradutor = GoogleTranslator(source='es', target='pt')
        traducao = tradutor.translate(texto)
        return traducao

    else:
        print("Idioma não reconhecido")
        return texto


def main():
    # Captura ou carrega a imagem
    caminho_imagem = ""
    '''opcao = input("Deseja capturar uma imagem (1) ou carregar de um arquivo (2)? ")
    if opcao == '1':
        imagem = capturar_imagem()
        imagem = Image.fromarray(cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB))
    elif opcao == '2':
        caminho_imagem = input("Digite o caminho da imagem: ")
        imagem = carregar_imagem(caminho_imagem)
    else:
        print("Opção inválida")
        return'''

    caminho_imagem = "leitura.jpg"
    imagem = carregar_imagem(caminho_imagem)

    # Converte a imagem para o formato esperado pela API
    imagem.save('temp.jpg')
    with open('temp.jpg', 'rb') as f:
        imagem_bytes = f.read()

    #falar_mensagem_inicial()

    # Envia a imagem para a API do Gemini
    texto = extrai_texto_da_imagem(caminho_imagem)
    print(f"[{len(texto)}] {texto}")
    os.remove("temp.jpg")

    idioma = detect(texto)

    texto = traduz(texto, idioma)

    # Fala o texto extraído
    # falar_texto(texto)

    # Perguntas sobre o texto
    fazer_perguntas()

if __name__ == "__main__":
    main()