#!/usr/bin/env python3
"""Inject Week 1 test quiz HTML into the Week 1 Review lesson."""
import json

QUIZ_HTML = '''
<div class="quiz-section-header">
  <h2>📝 Week 1 Test</h2>
  <p>35 questions covering Days 1–5 · Multiple choice, true/false, fill-in-the-particle, and reading match</p>
</div>

<div id="quizPreviousBanner" class="quiz-previous-banner"></div>

<div class="quiz-progress">
  <div class="quiz-progress-track">
    <div id="quizProgressFill" class="quiz-progress-fill"></div>
  </div>
  <div id="quizProgressText" class="quiz-progress-text">0 / 35 answered</div>
</div>

<div id="quizContainer">

<!-- ════════ DAY 1: Particles は/も/か, Numbers, Hiragana あ-こ ════════ -->

<!-- Q1 -->
<div class="quiz-question" data-topic="Particles" data-explanation="は (wa) marks the topic of the sentence." data-qnum="1">
  <div class="q-number">Q1</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">わたし ＿ がくせいです。(I am a student.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">は</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q2 -->
<div class="quiz-question" data-topic="Particles" data-explanation="も (mo) means 'also' or 'too' — it replaces は when indicating something is the same." data-qnum="2">
  <div class="q-number">Q2</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does the particle も mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">but</button>
    <button class="q-option" data-correct="true">also / too</button>
    <button class="q-option" data-correct="false">and</button>
    <button class="q-option" data-correct="false">or</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q3 -->
<div class="quiz-question" data-topic="Particles" data-explanation="か (ka) at the end of a sentence turns it into a question." data-qnum="3">
  <div class="q-number">Q3</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: Adding か at the end of a sentence makes it a question.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q4 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="か = ka, き = ki, く = ku, け = ke, こ = ko" data-qnum="4">
  <div class="q-number">Q4</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for く?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ka</button>
    <button class="q-option" data-correct="false">ki</button>
    <button class="q-option" data-correct="true">ku</button>
    <button class="q-option" data-correct="false">ke</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q5 -->
<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="じゅう (juu) = 10. Numbers combine: にじゅう = 20, さんじゅう = 30, etc." data-qnum="5">
  <div class="q-number">Q5</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What number is さんじゅうご (sanjuugo)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">25</button>
    <button class="q-option" data-correct="true">35</button>
    <button class="q-option" data-correct="false">53</button>
    <button class="q-option" data-correct="false">30</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q6 -->
<div class="quiz-question" data-topic="Vocabulary" data-explanation="せんせい (sensei) means teacher/professor. がくせい (gakusei) means student." data-qnum="6">
  <div class="q-number">Q6</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does せんせい (sensei) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Student</button>
    <button class="q-option" data-correct="true">Teacher</button>
    <button class="q-option" data-correct="false">Friend</button>
    <button class="q-option" data-correct="false">Parent</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q7 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="あ = a, い = i, う = u, え = e, お = o — the first five hiragana." data-qnum="7">
  <div class="q-number">Q7</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "e"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">あ</button>
    <button class="q-option" data-correct="false">い</button>
    <button class="q-option" data-correct="false">う</button>
    <button class="q-option" data-correct="true">え</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 2: この/その/あの, なん/だれ, の (possession), Hiragana さ-と ════════ -->

<!-- Q8 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="この (kono) = this (near speaker), その (sono) = that (near listener), あの (ano) = that over there." data-qnum="8">
  <div class="q-number">Q8</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does この (kono) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">this (near me)</button>
    <button class="q-option" data-correct="false">that (near you)</button>
    <button class="q-option" data-correct="false">that over there</button>
    <button class="q-option" data-correct="false">which</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q9 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="だれ (dare) = who. なん (nan) = what." data-qnum="9">
  <div class="q-number">Q9</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you say "who" in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">なに</button>
    <button class="q-option" data-correct="false">どこ</button>
    <button class="q-option" data-correct="true">だれ</button>
    <button class="q-option" data-correct="false">いくら</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q10 -->
<div class="quiz-question" data-topic="Particles" data-explanation="の (no) between two nouns shows possession: わたしのほん = my book." data-qnum="10">
  <div class="q-number">Q10</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">わたし ＿ ほん (my book)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="true">の</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">も</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q11 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="その (sono) refers to something near the listener — 'that (near you)'." data-qnum="11">
  <div class="q-number">Q11</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">＿ かばんは だれのですか。(Whose bag is that [near you]?)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">この</button>
    <button class="q-option" data-correct="true">その</button>
    <button class="q-option" data-correct="false">あの</button>
    <button class="q-option" data-correct="false">どの</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q12 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="さ = sa, し = shi, す = su, せ = se, そ = so" data-qnum="12">
  <div class="q-number">Q12</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for し?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">si</button>
    <button class="q-option" data-correct="true">shi</button>
    <button class="q-option" data-correct="false">chi</button>
    <button class="q-option" data-correct="false">tsu</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q13 -->
<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="ひゃく (hyaku) = 100. にひゃく = 200, さんびゃく = 300 (note: び not ひ)." data-qnum="13">
  <div class="q-number">Q13</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What number is にひゃくごじゅう (nihyaku gojuu)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">150</button>
    <button class="q-option" data-correct="true">250</button>
    <button class="q-option" data-correct="false">205</button>
    <button class="q-option" data-correct="false">500</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q14 -->
<div class="quiz-question" data-topic="Vocabulary" data-explanation="なん (nan) is the question word meaning 'what'. なんですか = What is it?" data-qnum="14">
  <div class="q-number">Q14</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: なん (nan) is used to ask "where".</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">True</button>
    <button class="q-option" data-correct="true">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 3: ここ/そこ/あそこ, どこ/いくら, の (categorization), Hiragana な-ほ ════════ -->

<!-- Q15 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="ここ = here (near speaker), そこ = there (near listener), あそこ = over there (far from both)." data-qnum="15">
  <div class="q-number">Q15</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does あそこ (asoko) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">here</button>
    <button class="q-option" data-correct="false">there (near you)</button>
    <button class="q-option" data-correct="true">over there (far from both)</button>
    <button class="q-option" data-correct="false">where</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q16 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="どこ (doko) = where. Used to ask about locations." data-qnum="16">
  <div class="q-number">Q16</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you ask "Where is the bank?" — ぎんこうは ＿ ですか。</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">なん</button>
    <button class="q-option" data-correct="false">だれ</button>
    <button class="q-option" data-correct="true">どこ</button>
    <button class="q-option" data-correct="false">いくら</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q17 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="いくら (ikura) = how much. Used when asking about price." data-qnum="17">
  <div class="q-number">Q17</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: いくら (ikura) is used to ask "how much" (price).</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q18 -->
<div class="quiz-question" data-topic="Particles" data-explanation="の (no) can also categorize: にほんの くるま = a Japanese car (car of Japan)." data-qnum="18">
  <div class="q-number">Q18</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">In にほんの くるま, what does の indicate?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Possession (Japan's car)</button>
    <button class="q-option" data-correct="true">Categorization (a Japanese car)</button>
    <button class="q-option" data-correct="false">Location (a car in Japan)</button>
    <button class="q-option" data-correct="false">Question marker</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q19 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="な = na, に = ni, ぬ = nu, ね = ne, の = no" data-qnum="19">
  <div class="q-number">Q19</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "nu"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">な</button>
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">ぬ</button>
    <button class="q-option" data-correct="false">ね</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q20 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="は = ha (but わ as particle), ひ = hi, ふ = fu, へ = he (but え as particle), ほ = ho" data-qnum="20">
  <div class="q-number">Q20</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for ふ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">hu</button>
    <button class="q-option" data-correct="true">fu</button>
    <button class="q-option" data-correct="false">su</button>
    <button class="q-option" data-correct="false">tsu</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q21 -->
<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="えん (en) = yen. Prices use number + えん: せんえん = 1000 yen." data-qnum="21">
  <div class="q-number">Q21</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you say "3000 yen" in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">さんひゃくえん</button>
    <button class="q-option" data-correct="true">さんぜんえん</button>
    <button class="q-option" data-correct="false">さんまんえん</button>
    <button class="q-option" data-correct="false">みっつえん</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 4: を, V-ます/V-ません, で/と, なに, Hiragana ま-よ ════════ -->

<!-- Q22 -->
<div class="quiz-question" data-topic="Particles" data-explanation="を (wo/o) marks the direct object of a verb: コーヒーを のみます = I drink coffee." data-qnum="22">
  <div class="q-number">Q22</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">コーヒー ＿ のみます。(I drink coffee.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">を</button>
    <button class="q-option" data-correct="false">で</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q23 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="V-ます (masu) is the polite present/future form. V-ません (masen) is the polite negative." data-qnum="23">
  <div class="q-number">Q23</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What is the polite negative form of たべます (tabemasu — to eat)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">たべました</button>
    <button class="q-option" data-correct="true">たべません</button>
    <button class="q-option" data-correct="false">たべませんでした</button>
    <button class="q-option" data-correct="false">たべる</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q24 -->
<div class="quiz-question" data-topic="Particles" data-explanation="で (de) indicates the means or location where an action takes place." data-qnum="24">
  <div class="q-number">Q24</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">がっこう ＿ べんきょうします。(I study at school.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">で</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">は</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q25 -->
<div class="quiz-question" data-topic="Particles" data-explanation="と (to) means 'with' when used between people: ともだちと = with a friend." data-qnum="25">
  <div class="q-number">Q25</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">ともだち ＿ ひるごはんを たべます。(I eat lunch with a friend.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">の</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="true">と</button>
    <button class="q-option" data-correct="false">も</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q26 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="なに (nani) is used to ask 'what' when it appears before を or a verb." data-qnum="26">
  <div class="q-number">Q26</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How would you ask "What do you eat?" — なにを ＿。</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">たべますか</button>
    <button class="q-option" data-correct="false">のみますか</button>
    <button class="q-option" data-correct="false">しますか</button>
    <button class="q-option" data-correct="false">いきますか</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q27 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="ま = ma, み = mi, む = mu, め = me, も = mo" data-qnum="27">
  <div class="q-number">Q27</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "mu"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ま</button>
    <button class="q-option" data-correct="false">み</button>
    <button class="q-option" data-correct="true">む</button>
    <button class="q-option" data-correct="false">め</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q28 -->
<div class="quiz-question" data-topic="Vocabulary" data-explanation="あさごはん = breakfast, ひるごはん = lunch, ばんごはん = dinner." data-qnum="28">
  <div class="q-number">Q28</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does ばんごはん mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Breakfast</button>
    <button class="q-option" data-correct="false">Lunch</button>
    <button class="q-option" data-correct="true">Dinner</button>
    <button class="q-option" data-correct="false">Snack</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 5: に/から/まで/ごろ, V-ました/V-ませんでした, Time, Hiragana ら-ん ════════ -->

<!-- Q29 -->
<div class="quiz-question" data-topic="Particles" data-explanation="に (ni) marks a specific point in time: 7じに = at 7 o'clock." data-qnum="29">
  <div class="q-number">Q29</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">7じ ＿ おきます。(I wake up at 7 o'clock.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="true">に</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">は</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q30 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="から (kara) = from, まで (made) = until/to. Used together: 9じから5じまで = from 9 to 5." data-qnum="30">
  <div class="q-number">Q30</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does 9じから 5じまで mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">At 9 and 5 o'clock</button>
    <button class="q-option" data-correct="true">From 9 o'clock to 5 o'clock</button>
    <button class="q-option" data-correct="false">Around 9 to around 5</button>
    <button class="q-option" data-correct="false">Before 9 and after 5</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q31 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="ごろ (goro) means 'around/about' for approximate time: 3じごろ = around 3 o'clock." data-qnum="31">
  <div class="q-number">Q31</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: ごろ (goro) means "around" when talking about approximate time.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q32 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="V-ました (mashita) is polite past tense. たべました = ate." data-qnum="32">
  <div class="q-number">Q32</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What is the polite past tense of のみます (nomimasu — to drink)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">のみません</button>
    <button class="q-option" data-correct="true">のみました</button>
    <button class="q-option" data-correct="false">のみませんでした</button>
    <button class="q-option" data-correct="false">のんだ</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q33 -->
<div class="quiz-question" data-topic="Grammar" data-explanation="V-ませんでした (masendeshita) is polite past negative. たべませんでした = did not eat." data-qnum="33">
  <div class="q-number">Q33</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: V-ませんでした is the polite past negative form (e.g., "did not eat").</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q34 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="ら = ra, り = ri, る = ru, れ = re, ろ = ro" data-qnum="34">
  <div class="q-number">Q34</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for れ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ra</button>
    <button class="q-option" data-correct="false">ri</button>
    <button class="q-option" data-correct="false">ru</button>
    <button class="q-option" data-correct="true">re</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- Q35 -->
<div class="quiz-question" data-topic="Hiragana" data-explanation="ん (n) is the only hiragana that is a standalone consonant — it doesn't pair with a vowel." data-qnum="35">
  <div class="q-number">Q35</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: ん is the only hiragana character that represents a single consonant sound without a vowel.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

</div><!-- end quizContainer -->

<div id="quizResults" class="quiz-results"></div>
'''

def main():
    with open('content/lessons/12645437.json', 'r') as f:
        data = json.load(f)

    # Append quiz HTML after existing content
    existing_html = data['html']
    data['html'] = existing_html + QUIZ_HTML

    with open('content/lessons/12645437.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Injected quiz HTML ({QUIZ_HTML.count('quiz-question')} questions)")
    print(f"   Total HTML length: {len(data['html'])}")

if __name__ == '__main__':
    main()
