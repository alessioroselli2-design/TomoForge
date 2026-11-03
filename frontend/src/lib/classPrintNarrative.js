// Original, concise presentation text for imported 2014/5e class catalogues.
// This is ONLY the printed card's editorial introduction. The complete
// verified reference text and the original historical source stay unchanged.
const CLASS_INTROS = Object.freeze({
  guerriero: "Maestri del combattimento, i guerrieri conoscono bene il pericolo e la morte che spesso incontrano sul campo di battaglia. Sono addestrati nell'uso di un'ampia varietà di armi e armature e uniscono tecnica, disciplina e resistenza per eccellere in battaglia.",
  druido: "Custodi delle forze naturali, i druidi traggono magia dalla terra, dagli animali e dagli elementi. Sanno assumere forme selvatiche e proteggono l'equilibrio tra i viventi. In battaglia alternano incantesimi, ingegno e la forza della natura.",
  barbaro: "I barbari affrontano il combattimento con un'energia travolgente. La loro furia è una forza primordiale alimentata dall'istinto, dal coraggio e dalla resistenza. Sono guerrieri tenaci, abituati a superare il pericolo contando sulla propria determinazione.",
  bardo: "I bardi intrecciano parole, musica e magia per ispirare gli alleati e influenzare il mondo. Viaggiatori, narratori e conoscitori di antiche tradizioni, trasformano l'arte in uno strumento di potere, astuzia e avventura.",
  chierico: "I chierici incanalano il potere divino attraverso la fede e la devozione. Guaritori, protettori o combattenti sacri, mettono la propria magia al servizio degli ideali della loro divinità e affrontano le sfide con convinzione.",
  ladro: "Agili e astuti, i ladri si affidano a precisione, intuito e abilità fuori dal comune. Possono agire nell'ombra, superare ostacoli e cogliere le opportunità che sfuggono agli altri. La loro versatilità li rende preziosi in ogni avventura.",
  mago: "I maghi studiano la magia arcana e ne padroneggiano i segreti attraverso ricerca, studio e sperimentazione. Il loro sapere permette di plasmare energie, creare illusioni e risolvere sfide con incantesimi di straordinaria varietà.",
  monaco: "I monaci disciplinano corpo e mente per raggiungere un'armonia straordinaria. Grazie all'allenamento e al controllo della propria energia interiore, uniscono rapidità, precisione e consapevolezza nei movimenti e nel combattimento.",
  paladino: "I paladini dedicano la propria vita a un giuramento e agli ideali che li guidano. La loro determinazione dà forza ai compagni e li sostiene nelle battaglie, dove combinano abilità marziale, coraggio e potere sacro.",
  ranger: "Esploratori esperti delle terre selvagge, i ranger conoscono le tracce, i pericoli e le creature della natura. Uniscono abilità marziale, intuito e magia per proteggere i compagni e affrontare minacce lontane dalla civiltà.",
  stregone: "Gli stregoni possiedono un legame innato con la magia arcana. Il loro potere nasce da un'origine straordinaria e si manifesta attraverso incantesimi plasmati dall'istinto e dalla volontà, senza richiedere lo studio dei maghi.",
  warlock: "I warlock ottengono conoscenze e poteri arcani attraverso un patto con un'entità misteriosa. Cercano segreti nascosti e nuove possibilità magiche, usando doni singolari che riflettono la natura del loro legame.",
  artificiere: "Gli artificieri combinano ingegno, conoscenza magica e abilità artigianale. Infondono potere in strumenti e oggetti, inventando soluzioni sorprendenti per esplorare, proteggere e combattere.",
});
export const classPrintNarrative=(card={},legacy="")=>{
  const provided=String(card.description||"").trim();
  // Personal descriptions and custom classes always keep the user's exact text.
  const referenceSummary=/\bD&D\s*5e\b/i.test(provided)
    && /\b(?:Manuale|Dado Vita|Tiri salvezza|Privilegi)\b/i.test(provided);
  const key=String(card.name||"").toLocaleLowerCase("it").trim();
  const editorial=referenceSummary ? CLASS_INTROS[key] : "";
  return editorial||provided||String(legacy||"").trim();
};
