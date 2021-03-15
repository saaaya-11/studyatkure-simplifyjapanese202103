import sys
import os
import re
import webbrowser
from flask import *
from janome.tokenizer import Tokenizer
from nltk.corpus import wordnet
import csv
from gensim.models.phrases import Phrases, Phraser
import pandas as pd
import shutil
import pyttsx3
import requests
import chardet
from bs4 import BeautifulSoup as bs

app=Flask(__name__)

class process(): #main processes
    def translate(): # short sentences
        t=Tokenizer("dic/user_dic.csv", udic_enc="cp932") # read user defined dictionary, "user_dic.csv" in dic folder
        inputs=str(request.form["inputs"]) # 'inputs' is the string gotten as POST
        with open('dic/logs.txt', 'a', encoding='utf-8') as f_logs: # add the 'inputs' to "log.txt"
            f_logs.write(inputs+'\n')
        
        tokens=t.tokenize(inputs) 
        prevPart=" " # part_of_speech of a previous word
        outputs="　" # text translated
        phonetics="" #pronounciation
        for token in tokens:
            allhiragana=1 #flag to check whether the text has only hiragana or katakana
            phonetics+=token.phonetic
            for r in (token.surface):
                if not((12353<=ord(r) and ord(r)<=12435) or (12449<=ord(r) and ord(r)<=12534)): #if(not hiragana or not katakana) # ((13312<=ord(r) and ord(r)<=40918) or (11904<=ord(r) and ord(r)<=12245))?? 
                    allhiragana=0 # turn off the flag
                    break
            crtPart=token.part_of_speech.split(',')[0] # part_of_speech of the current word
            if prevPart=="名詞" and crtPart=="助動詞" and token.surface=="だ": 
                outputs+=("です"+'　') # transform だ to です
            elif (prevPart=="名詞" or prevPart=="助詞") and crtPart=="形容詞" and token.surface=="ない":
                outputs+=("ないです"+'　') #transform ない to ないです
            elif prevPart=="動詞" and crtPart=="助動詞" and token.surface=="ない":
                outputs+=("ません"+'　') #transform ない　to ません
            elif token.reading=='*' or allhiragana==1 or crtPart=="記号": #if (the flag is still on or no reading)
                outputs+=(token.surface+'　')  # no transformation
            else:
                #surface_list=list(token.surface) #surfaces of each words
                reading_list=list(token.reading) #readings of each words
                outputs+=(token.surface+"(") 
                for r in (reading_list):
                    if 12449<=ord(r)<=12534: # if the reading is katakana
                        char1=chr(ord(r)-96) # katakana to hiragana
                        outputs+=(char1)
                    else:
                        outputs+=(r)
                #surface_list.clear() #clear the list
                reading_list.clear() #clear the list
                outputs+=(')　')
            prevPart=token.part_of_speech.split(',')[0] 
        outputs+=('\n')
        #print(readings)
        #engine=pyttsx3.init()
        #voices = engine.getProperty('voices')
        #engine.setProperty("voice", voices[1].id)
        #engine.setProperty('rate', 40)
        #engine.save_to_file(phonetics,"templates/media/read.mp3")
        #engine.runAndWait()
        #print("saved")
        return outputs
    def rubies(inputs): # website
        t=Tokenizer("dic/user_dic.csv", udic_enc="cp932") # read user defined dictionary, "user_dic.csv" in dic folder
        tokens=t.tokenize(inputs) 
        prevPart=" " # part_of_speech of a previous word
        outputs=[] # text translated
        for token in tokens:
            allhiragana=1 #flag to check whether the text has only hiragana or katakana
            for r in (token.surface):
                if not((12353<=ord(r) and ord(r)<=12435) or (12449<=ord(r) and ord(r)<=12534)): #if(not hiragana or not katakana) # ((13312<=ord(r) and ord(r)<=40918) or (11904<=ord(r) and ord(r)<=12245))?? 
                    allhiragana=0 # turn off the flag
                    break
            crtPart=token.part_of_speech.split(',')[0] # part_of_speech of the current word
            if prevPart=="名詞" and crtPart=="助動詞" and token.surface=="だ": 
                outputs.append([0,"です"]) #  mode 0=>no ruby, transform だ to です
            elif (prevPart=="名詞" or prevPart=="助詞") and crtPart=="形容詞" and token.surface=="ない":
                outputs.append([0,"ないです"]) #transform ない to ないです
            elif prevPart=="動詞" and crtPart=="助動詞" and token.surface=="ない":
                outputs.append([0,"ません"]) #transform ない　to ません
            elif token.reading=='*' or allhiragana==1 or crtPart=="記号": #if ( no reading or the flag is still on)
                outputs.append([0,token.surface])  # no transformation
            else: 
                surface_list=list(token.surface) #surfaces of each words
                reading_list=list(token.reading) #readings of each words
                ruby=""
                for r in (reading_list):
                    if 12449<=ord(r)<=12534: # if the reading is katakana
                        char1=chr(ord(r)-96) # katakana to hiragana
                        ruby+=(char1)
                    else:
                        ruby+=(r)
                surface_list.clear() #clear the list
                reading_list.clear() #clear the list
                outputs.append([1, token.surface, ruby])  # mode 1=> ruby exists, original form, ruby
            prevPart=token.part_of_speech.split(',')[0] 
        return outputs
    def synonym():
        detail="<b>ーーーちかい　いみ　の　ことばーーー</b><br>" #html text
        t=Tokenizer("dic/user_dic.csv", udic_enc="cp932")
        inputs=str(request.form["inputs"])
        tokens=t.tokenize(inputs)
        nosyn=0
        for token in tokens:
            if token.part_of_speech.split(',')[0]!="名詞" and token.part_of_speech.split(',')[0]!="動詞":
                continue
            nosyn=1
            synsets=wordnet.synsets(token.base_form, lang='jpn')
            detail+="<span class='detail-word'>"
            detail+=token.surface
            detail+="</span> : "
            for syn in synsets:
                detail+=str(syn.lemma_names("jpn")[0:3])
                detail+=" / "
            detail+="<br>"
        if nosyn==0:
            return " "
        return Markup(detail)
class learn():
    def judge(word):
        tokenizer=Tokenizer("dic/user_dic_cpy.csv", udic_enc="cp932")
        word_list=word.split("_")
        word=word.replace("_", "")
        tokens=tokenizer.tokenize(word)
        if len(tokens)==1 or re.search("\s+", word): #空白文字が含まれてたら除外
            return pd.Series(["","",""])
        if word_list[0]=="年" or word_list[0]=="年度":
            return pd.Series(["","",""])
        part0=tokens[-1].part_of_speech.split(',')[0] #[-1]は配列の最後尾の要素
        if part0=="助詞" or part0=="助動詞":
            del tokens[-1]
            del word_list[-1]
            word="".join(word_list)
            if len(tokens)==1:
                return pd.Series([word,""])
        reading=""
        for num, token in enumerate(tokens):
            #surFace=token.surface
            part0=token.part_of_speech.split(',')[0]
            part1=token.part_of_speech.split(',')[1]
            part2=token.part_of_speech.split(',')[2]
            reading+=token.reading
            #baceForm=token.base_form
            #inflForm=token.infl_form
            if num==0:
                if part0==u"接頭詞": #最初が接頭詞ならば
                    continue         #次の単語へ
            if part0!=u'名詞':
                return pd.Series([word,"", False])
            elif part0=="名詞" and (part1==u'数' or part2=="助数詞"):
                return pd.Series([word,"", False])
            else:
                continue
        return pd.Series([word, reading, True])
    def compw():
        shutil.copy("dic/user_dic.csv", "dic/user_dic_cpy.csv")
        #print("インポートするテキストファイル：")
        #filename=input()
        with open("dic/logs.txt", 'r', encoding='utf-8') as file_txt:
            logtxt=[s.strip() for s in file_txt.readlines()]
        tokenizer=Tokenizer("dic/user_dic_cpy.csv", udic_enc="cp932")
        corpus=[]
        for text_list in logtxt:
            tokens=tokenizer.tokenize(text_list)
            corpus.append([token.surface for token in tokens])
        corpus_phrase=corpus
        gramCnt=5
        for i in range(gramCnt-1):
            phrases=Phrases(corpus_phrase, min_count=5, threshold=10.0)
            phraser=Phraser(phrases)
            transformed=list(phraser[corpus_phrase])
            corpus_phrase=transformed
        words_df=pd.DataFrame()
        for sentence in corpus_phrase:
            for word in sentence:
                if word.find('_')>=0:
                    words_df=words_df.append([word]) #新しく行を追加
        words_df.columns=["複合語候補"]
        words_df["回数"]=0
        words_df=(words_df.groupby("複合語候補")[["複合語候補"]].count())
        words_df=(words_df.rename(columns={'複合語候補': '回数'})
            .reset_index()
            .sort_values(by="回数", ascending=False)
            .reset_index(drop=True))
        print("完了")
        words_df=(pd.concat([words_df, words_df["複合語候補"].apply(learn.judge)], axis=1)
                    .rename(columns={0:"単語", 1:"読み", 2:"判定"}))
        words_judge=(words_df.groupby(["単語", "読み", "判定"])["回数"].sum()
                .reset_index()
                .rename(columns={0:"回数"})
                .sort_values(by="回数",ascending=False))
        words_dic=words_judge[(words_judge["判定"]==True) & (words_judge["回数"]>=6)]
        if not words_dic.empty:
            words_dic["paramater"]="-1,-1,1000,名詞,一般,*,*,*,*,%s,%s,%s"
            words_dic=pd.concat(
                [words_dic['単語'],words_dic['paramater']
                .str.split(',', expand=True)], axis=1)
            words_dic[9]=words_dic["単語"]
            words_dic[10]=words_judge["読み"]
            words_dic[11]=words_judge["読み"]
            words_dic
            words_dic.to_csv("dic/user_dic.csv", sep=",", mode='a', index=False,header=False,encoding='cp932') 
        print("updated")
        return

@app.route("/", methods=["GET", "POST"])
def getInput():
    if request.method=="GET":
        return render_template('index.html', title="やさしい日本語")
    else:
        original=request.form['inputs']
        translated=process.translate()
        detail=process.synonym()
        try:
            return render_template('index.html', title="やさしい日本語", original=original, translated=translated, detail=detail)
        except:
            return render_template('index.html', title="やさしい日本語", original=original)

@app.route("/templates/media/<path:filename>")
def play(filename):
    return send_from_directory("templates/media/", filename)

@app.route("/webpage-translate", methods=["GET", "POST"])
def getURL():
    if request.method=="GET":
        return render_template('webpage-translate.html', title="やさしい日本語")
    else:
        return render_template('webpage-translate.html')
@app.route("/rubied", methods=["GET", "POST"])
def renderpage():
    if request.method=="GET":
        pageURL=request.args.get('pageURL')
        res=requests.get(pageURL)
        soup=bs(res.content, "html.parser")
        """
        for an in soup.find_all("a"):
            url_href=an.get("href")
            an["href"]="http://localhost:5000/rubied?pageURL="+pageURL+url_href
        """
        for pn in soup.find_all("p"):
            newpn=process.rubies(pn.text)
            pn.clear()
            for m in newpn:
                if m[0]==0:
                    pn.append(m[1])
                else:
                    rubytag=soup.new_tag('ruby')
                    rubytag.string=m[1]
                    rptag1=soup.new_tag('rp')
                    rptag1.string="("
                    rttag=soup.new_tag('rt')
                    rttag.string=m[2]
                    rptag2=soup.new_tag('rp')
                    rptag2.string=")"
                    rubytag.append(rptag1)
                    rubytag.append(rttag)
                    rubytag.append(rptag2)
                    pn.append(rubytag)
        originalheadlist=soup.head.contents
        originalheadstr="".join(map(str,originalheadlist)) #list to string
        headhtml="<head><base href=\""+pageURL+"\">"+originalheadstr+"</head>"
        originalbodylist=soup.body.contents
        originalbodystr="".join(map(str,originalbodylist)) #list to string
        bodyhtml="<body>"+originalbodystr+"</body>"
        #print(headhtml)
        return render_template('rubied.html', headhtml=Markup(headhtml), bodyhtml=Markup(bodyhtml), title="ルビ付き", URLtoOpen=pageURL)
    else:
        return render_template('webpage-translate.html')
if __name__=="__main__":
    learn.compw()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)