#coding: utf-8
import sys
import itertools
import re

def is_doc_info(knp_line):
  return knp_line[0] == '#'

def is_chunk(knp_line):
  return knp_line[0] == '*'

def is_basic_phrase(knp_line):
  return knp_line[0] == '+'

def is_EOS(knp_line):
  return knp_line == "EOS"

def is_token(knp_line):
  return (not is_doc_info(knp_line)) and (not is_chunk(knp_line)) and (not is_basic_phrase(knp_line)) and (not is_EOS(knp_line))

def is_neg_cue(knp_line):
  auxiliary_verbs = ["ない", "ぬ"]
  suffix_words = ["ない"]
  prefix_words = ["非", "不", "無", "未", "反", "異"]
  content_words = ["無い", "無し"] #prefixの条件で必ず通ってしまうので、実装的にはコメントアウトして良い

  #"のではない"
  #"わけではない"
  #"わけにはいかない"

  if(is_token(knp_line)):
    base = knp_line.split(' ')[2]

    flag0 = base in auxiliary_verbs
    flag1 = False
    for sf_w in suffix_words:
      flag1 = flag1 or base.endswith(sf_w)

    flag2 = False
    for pf_w in prefix_words:
      flag2 = flag2 or base.startswith(pf_w)

    flag3 = any([(cw in base) for cw in content_words])

    return any([flag0, flag1, flag2, flag3])
  else:
    return False

#1文に対するKNPの解析結果を受け取り、その文中に存在する否定要素を返す
#返り値はknp_linesでのインデックスのリスト

def get_cues(knp_lines):
  ans = [i for i,line in enumerate(knp_lines) if is_neg_cue(line)]
  return ans


#特定のキーワードが含まれているかどうか、キューから文頭に向かって調べる
#見つかった場合、そのキーワードのインデックス(のリスト)を返す。
#複数見つかるかもしれないことを考慮 → しません
#代表表記などを利用したかったが、煩雑なので「表層形」のみ見る
#漢字かな交じりの語は考慮しない。
def detect_focus_with_keywords(knp_lines, cue_index, keywords):
  for index in xrange(cue_index-1, -1, -1):
    if(is_token(knp_lines[index])):
      if(knp_lines[index].split(' ')[0] in keywords):
        chunk_ind = get_chunk_ind_of_token(knp_lines, index)
        tokens = get_tokens_of_chunk(knp_lines, chunk_ind)
        return tokens
      elif((knp_lines[index].split(' ')[2] in ["、"]) or (knp_lines[index].split(' ')[9] == "基本条件形")):
        #FIXME
        #「~スルと」の場合が未実装
        break

  return []

#Sec 4.8 syntactic pattern "As for"
def detect_focus_with_syntactic_pattern_as_for(knp_lines, cue_index):
  #「は」を含んでいる数は?
  chunk_inds = [i for i,line in enumerate(knp_lines) if is_chunk(line)]
  wa_num = len([chunk_ind for chunk_ind in chunk_inds if knp_lines[get_tokens_of_chunk(knp_lines, chunk_ind)[-1]].split(' ')[0] == 'は'])

  #「で の」や「で は」を後ろから探索するので、indexは0にならないようにする。indexが0になると、その前を見ようとする時にindexが-1になり、リストの未尾を見てバグる
  for index in xrange(cue_index-1, 0, -1):
    prev = index - 1
    if(prev < 0):
      raise Exception('IndexOutOfBoundsException')

    if(is_token(knp_lines[index])):
      if((knp_lines[prev].split(' ')[0] == 'で' and knp_lines[index].split(' ')[0] == 'の' and wa_num >= 1) or (knp_lines[prev].split(' ')[0] == 'で' and knp_lines[index].split(' ')[0] == 'は' and wa_num >= 2)):
        return get_chunk_tokens(knp_lines, index)
      elif((knp_lines[index].split(' ')[2] in ["、"]) or (knp_lines[index].split(' ')[9] == "基本条件形")):
        #FIXME
        #「~スルと」の場合が未実装
        break

  return []

#Sec 4.9 Immediate 'ni' case
def detect_focus_with_immediate_ni_case(knp_lines, cue_index):
  ans = []

  #「○○ に」を後ろから探索するので、indexは0にならないようにする。indexが0になると、その前を見ようとする時にindexが-1になり、リストの未尾を見てバグる
  for index in xrange(cue_index-1, 0, -1):
    prev = index - 1
    if(prev < 0):
      raise Exception('IndexOutOfBoundsException')

    if(is_token(knp_lines[index])):
      if(knp_lines[index].split(' ')[0] == 'に' and is_token(knp_lines[prev])):
        chunk_ind = get_chunk_ind_of_token(knp_lines, index)
        tokens = get_tokens_of_chunk(knp_lines, chunk_ind)
        return tokens
      elif((knp_lines[index].split(' ')[2] in ["、"]) or (knp_lines[index].split(' ')[9] == "基本条件形")):
        #FIXME
        #「~スルと」の場合が未実装
        break

  return ans

def detect_focus_with_numeral_with_particle_mo(knp_lines, cue_index):
  ans = []

  chunk_inds = [i for i in xrange(0,cue_index) if is_chunk(knp_lines[i])]
  for chunk_ind in chunk_inds[::-1]:
    tokens = get_tokens_of_chunk(knp_lines, chunk_ind)
    lines = map(lambda i: knp_lines[i], tokens)

    if(any([line.split(' ')[0].decode("utf-8").isnumeric() for line in lines]) and lines[-1].split(' ')[0] == 'も'):
      return tokens

  return ans

def zip_with_index(lst):
  return [(i, lst[i]) for i in xrange(0, len(lst))]

def detect_focus_with_syntactic_pattern_while(knp_lines, cue_index):
  knp_ind_tokens = [(i, line) for i, line in enumerate(knp_lines) if is_token(line) and i < cue_index]
  # 「hoge の 方 の」を後ろから調べるので、最後の「の」のインデックスは3になることはない。
  for i in xrange(len(knp_ind_tokens)-1, 3, -1):
    ind = knp_ind_tokens[i][0]
    line = knp_ind_tokens[i][1]

    if(line.split(' ')[0] == 'の' and knp_ind_tokens[i-1][1].split(' ')[0] == '方' and knp_ind_tokens[i-2][1].split(' ')[0] == 'の'):
      return get_chunk_tokens(knp_lines, knp_ind_tokens[i-2][0])
    elif((line.split(' ')[2] in ["、"]) or (line.split(' ')[9] == "基本条件形")):
      #FIXME
      #「~スルと」の場合が未実装
      break

  return []

#KNPの解析結果と、あるトークンのインデックスを引数にとり、
#そのトークンが含まれているチャンクに関する行のインデックスを返す
def get_chunk_ind_of_token(knp_lines, token_ind):
  ans = -1

  if(not is_token(knp_lines[token_ind])):
    raise Exception('Argument Error')

  for i in xrange(token_ind):
    line = knp_lines[i]
    if(is_chunk(line)):
      ans = i

  return ans

#同様の方法で基本句のかかり先を求めるメソッドを作ることもできるが、使わないかもしれないので今は抽象化しない。
#あるチャンクにかかっているチャンクのインデックスのリストを返す
def get_chunk_modifiers(knp_lines, chunk_ind):
  chunk_num = int(knp_lines[chunk_ind].split(' ')[1])
  pattern = re.compile(r"^\* \d+ %d[DP] " % chunk_num)
  return [i for i,line in enumerate(knp_lines) if is_chunk(line) and re.match(pattern, line)]

#KNPの解析結果と、あるチャンクのインデックスを引数にとり、
#そのチャンクに属するトークンのインデックスのリストを返す
def get_tokens_of_chunk(knp_lines, chunk_ind):
  if(not is_chunk(knp_lines[chunk_ind])):
    raise Exception('Argument Error')

  lines_with_ind = zip_with_index(knp_lines)
  next_chunk_inds = [i for i,line in lines_with_ind if is_chunk(line) and chunk_ind < i]
  next_chunk_ind = next_chunk_inds[0] if (len(next_chunk_inds) > 0) else len(knp_lines) #問題としているチャンクが文末のチャンクだった場合、処理を変更
  token_inds = [i for i, line in lines_with_ind if is_token(line)]
  ans = [i for i in token_inds if chunk_ind < i < next_chunk_ind]

  return ans

#その中から、場所+(に)はとなっている節を探す
#そのチャンクの形態素が「カテゴリ:場所」を含んでいる
#かつ、そのチャンクが「は」で終わる
def detect_focus_with_locative_with_particle_wa(knp_lines, cue_index):
  ans = []


  cue_chunk_ind = get_chunk_ind_of_token(knp_lines, cue_index)
  modifier_chunks = get_chunk_modifiers(knp_lines, cue_chunk_ind)

  #かかっているチャンクは複数ある場合があるが、「後ろから」探す
  #そのほうが、正しく係っている可能性が高い
  for chunk_ind in reversed(modifier_chunks):
    tokens = get_tokens_of_chunk(knp_lines, chunk_ind)
    lines = map(lambda i: knp_lines[i], tokens)
    if(any([("カテゴリ:場所" in line) for line in lines]) and lines[-1].split(' ')[0] == 'は'):
      return tokens

  return ans

#KNPの解析結果と、あるトークンのインデックスを引数にとり、
#そのトークンが含まれる文節(チャンク)のトークンのリストを返す
def get_chunk_tokens(knp_lines, token_ind):
  chunks_and_tokens = [ (i, line) for i, line in enumerate(knp_lines) if is_token(line) or is_chunk(line)]
  a = [i for i in itertools.takewhile(lambda (i,line): i <= token_ind or is_token(line), chunks_and_tokens)]
  b = [i for i in itertools.takewhile(lambda (i,line): is_token(line), a[::-1])]
  ans = map(lambda (i,line): i, b[::-1])

  return ans

#Sec 4.14
def detect_focus_with_syntactic_pattern_for_adnominal_no_phrase(knp_lines, cue_index):
  cue_chunk = get_chunk_ind_of_token(knp_lines, cue_index)
  modifiers_of_cue = get_chunk_modifiers(knp_lines, cue_chunk)
  if(len(modifiers_of_cue) == 0):
    return []
  else:
    chunks_end_with_wa = [modifier for modifier in modifiers_of_cue if knp_lines[get_tokens_of_chunk(knp_lines, modifier)[-1]].split(' ')[0] == 'は']
    for wa_chunk in chunks_end_with_wa:
      modifiers_of_wa_chunk = get_chunk_modifiers(knp_lines, wa_chunk)
      if(len(modifiers_of_wa_chunk) == 0):
        return []
      else:
        modifiers_with_no_case = [modifier_ind for modifier_ind in modifiers_of_wa_chunk if knp_lines[get_tokens_of_chunk(knp_lines, modifier_ind)[-1]].split(' ')[0] == 'の']
        if(len(modifiers_with_no_case) == 1):
          return get_tokens_of_chunk(knp_lines, modifiers_with_no_case[0])
        elif(len(modifiers_with_no_case) > 1):
          raise Exception('Need to think')
        else:
          pass

  return []

#Sec 4.16
#先頭のチャンクは「に」で終わっているか?
def detect_focus_with_ni_case_at_the_beginning_of_the_sentence(knp_lines, cue_index):
  top_chunk_ind = [i for i, line in zip_with_index(knp_lines) if is_chunk(line)][0]
  tokens = get_tokens_of_chunk(knp_lines, top_chunk_ind)

  return tokens if (knp_lines[tokens[-1]].split(' ')[0] == 'に') else []


#KNPの解析結果とキューのインデックスを引数として、
#焦点のインデックスのリストを返す
#
def detect_foc(knp_lines, cue_index):
  foc_list = []

  #Sec 4.1
  foc_list = detect_focus_with_keywords(knp_lines, cue_index, ["しか", "だけ", "まで", "ほど"])

  #Sec 4.2
  if(len(foc_list) == 0):
    keywords = """
余り
あまり
大方
大かた
おお方
おおかた
大旨
大むね
おお旨
概ね
おおむね
おおよそ
凡そ
およそ
大抵
大てい
たい抵
たいてい
大体
大たい
だい体
だいたい
殆んど
殆ど
ほとんど
ほぼ
たっぷり
なかなか
"""[1:-1].split('\n')
    foc_list = detect_focus_with_keywords(knp_lines, cue_index, keywords)

  #Sec 4.3
  if(len(foc_list) == 0):
    #「時相名詞である」という条件を利用してメソッドを書いたほうがいい?
    foc_list = detect_focus_with_keywords(knp_lines, cue_index, ["今回", "次回", "以来"])

  #Sec 4.4
  if(len(foc_list) == 0):
    keywords = """
頻繁に
ひんぱんに
ひん繁に
頻ぱんに
しょっちゅう
よく
いつも
ときたま
たまに
めったに
滅多に
まれに
稀に
希に
しばしば
ときどき
時どき
時々
時おり
時折
ときおり
おりおり
たえず
絶えず
しきりに
常に
しじゅう
"""[1:-1].split('\n')
    foc_list = detect_focus_with_keywords(knp_lines, cue_index, keywords)

  #Sec 4.5
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_keywords(knp_lines, cue_index, ["うまく", "上手く", "ゆっくり", "自然"])

  # #Sec 4.6
  # if(len(foc_list) == 0):
  #   #もし「乗り切れ ない」が「乗り 切れ ない」に分割されると「切れ」が焦点として判定される。
  #   foc_list = detect_focus_with_keywords(knp_lines, cue_index, ["きれ", "切れ"])

  #Sec 4.7
  if(len(foc_list) == 0):
    #単語の先頭の「全」は見ていない。つまり、「全部」などは反応しない。
    foc_list = detect_focus_with_keywords(knp_lines, cue_index, ["全", "全て", "すべて"])

  #Sec 4.8
  if(len(foc_list) == 0):
    #「では」、「での」
    foc_list = detect_focus_with_syntactic_pattern_as_for(knp_lines, cue_index)

  #Sec 4.9
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_immediate_ni_case(knp_lines, cue_index)

  #Sec 4.10
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_numeral_with_particle_mo(knp_lines, cue_index)

  #Sec 4.11
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_syntactic_pattern_while(knp_lines, cue_index)

  #Sec 4.12
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_locative_with_particle_wa(knp_lines, cue_index)

  #Sec 4.13
  #FIXME

  #Sec 4.14
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_syntactic_pattern_for_adnominal_no_phrase(knp_lines, cue_index)

  #Sec 4.15
  #FIXME

  #Sec 4.16
  if(len(foc_list) == 0):
    foc_list = detect_focus_with_ni_case_at_the_beginning_of_the_sentence(knp_lines, cue_index)

  return foc_list



#文字列のリストを引数として取る
#knp_linesは1つの文をKNPで解析した時の解析結果の文字列→'#'から始まり、"EOS"で終わるもの。1行がリストの1要素
def sentence_func(knp_lines):
  cues = get_cues(knp_lines)
  for cue_ind in cues:
    foc_list = detect_foc(knp_lines, cue_ind)
    sys.stdout.write("".join(map(lambda i: str(knp_lines[i].split(' ')[0]), foc_list))+ ",")

    # sys.stdout.write(str(foc_list) + ",")
  print ""


def main():
  # sentence_id = 1
  knp_lines = []

  for line in sys.stdin:
    line = line.rstrip()
    knp_lines.append(line)

    if line == "EOS":
      sentence_func(knp_lines)
      knp_lines = []

if __name__ == "__main__":
  main()


