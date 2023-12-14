'use strict';
/* 1. show map using Leaflet library. (L comes from the Leaflet library) */
/*
const map = L.map('map', {tap: false});
L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
  subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
}).addTo(map);
map.setView([51.8, -1.7], 7);
//alempi normaali kartta, ylempi satelliittikuvakartta
*/

let map = L.map('map').setView([51.8, -1.7], 7);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

// global variables

/*
//  voidaan asettaa alemmat minipelit käynnistymään tällä, game_id:n täytyy
//   olla asetettu ennen peliä; lataa tallennus tai luo uusi pelaaja ennen
const diceBtn = document.getElementById('diceBtn');
diceBtn.addEventListener('click', dicegame);
*/
// käytetään modalin esittämiseen, dialog.showModal(), dialog.close()
const dialog = document.querySelector('dialog');
//tämän sisään laitetaan modalissa näytettävää sisältöä, tyhjennetään ensin vanhoista
const div = dialog.querySelector('#dialog-div');
// pelin aloituspainike valikossa
const startGameBtn = document.getElementById('startGame-Btn');
//dialogin sulkija(X-painike)
const span = dialog.querySelector('span');
span.addEventListener('click', () => {
  dialog.close();
});
//highscore-nappula
const highScoreBtn = document.getElementById('highscore-Btn');
highScoreBtn.addEventListener('click', showHighscores);

//markerien lista, alkuperäinen: let mapMarkers = [];
const airportMarkers = L.featureGroup().addTo(map);

// game_id:n avulla voidaan hakea tietoja backendistä sekä päivittää niitä
// käskyissä
let game_id = 0;
let screen_name = 'default';
let visited_heliports = [];
let connected_heliports = [];
let heliports_in_range = [];
let stats = 'null';

//funktiot

// hakee tallennetut pelit backendistä ja näyttää ne modalissa
// painettavina elementteinä joiden perusteella ladataan game_id
async function getSavedGames() {
  div.innerHTML = '';
  try {

    const response = await fetch(
        `http://127.0.0.1:3000/get_games`);
    if (!response.ok) throw new Error('loading games failed');
    const infoJSON = await response.json();
    const save_list = document.createElement('span');
    save_list.id = 'save_list';
    save_list.classList.add('vertical-menu');
    const text = document.createTextNode('Choose saved game');/*(JSON.stringify(infoJSON))*/
    const menuP = document.createElement('h2');
    menuP.appendChild(text);
    save_list.appendChild(menuP);
    for (const info of infoJSON) {
      const text = document.createTextNode(info.screen_name);/*(JSON.stringify(infoJSON))*/
      const infoEle = document.createElement('p');
      infoEle.addEventListener('click', () => {
        game_id = info.id;
        getStartInfo();
        dialog.close();
        div.innerHTML = '';
      });
      infoEle.appendChild(text);
      save_list.appendChild(infoEle);
    }
    div.appendChild(save_list);
  } catch (error) {
    console.log(error.message);
  }
}

//kutsutaan kun pelaaja löytää kentältä dicegame-goalin; näyttää modalin jolla
//pelaaja päättää millä panoksella pelaa tai jättää pelin pelaamatta.
//Jos pelaaja haluaa pelata, lähetetään backendiin käsky, eli playDice() kutsutaan

function dicegame() {
  // Open the modal when the button is clicked
  div.innerHTML = '';
  //nappula dicegamen hyväksymiselle
  const btn3 = document.createElement('input');
  btn3.type = 'submit';
  btn3.value = 'Play';
  const btn5 = document.createElement('button');
  btn5.innerText = 'Not interested';
  btn5.addEventListener('click', () => dialog.close());

  const form2 = document.createElement('form');
  const bet = document.createElement('input');

  form2.appendChild(bet);
  form2.appendChild(btn3);
  form2.addEventListener('submit', (evt) => {
    evt.preventDefault();
    playDice(bet.value);
  });

  bet.type = 'number';
  bet.min = '1';
  bet.max = stats.gas_left;
  const img = document.createElement('img');
  img.src = 'shadysquirrel.jpg';
  img.style = 'width:100%';
  div.appendChild(img);
  const text = document.createTextNode(
      'Shady squirrel offers you to play Dice, you win if 2 dices match! Place your bet, if you want to play.');
  const h2 = document.createElement('h2');
  h2.appendChild(text);
  div.appendChild(h2);
  div.appendChild(form2);

  div.appendChild(btn5);

  dialog.showModal();
}

//lähettää backendiin minipelikäskyn ja näyttää sen tuloksen modalissa
async function playDice(bet) {
  div.innerHTML = '';
  try {
    const response = await fetch(
        `http://127.0.0.1:3000/play_dice/${game_id}/${bet}`);
    if (!response.ok) throw new Error('loading games failed');
    const infoJSON = await response.json();
    const save_list = document.createElement('span');
    let text = '';
    if (infoJSON.result == 'Won')
      text = document.createTextNode('You won!');/*(JSON.stringify(infoJSON))*/
    else if (infoJSON.result == 'Lost')
      text = document.createTextNode('You lost!');/*(JSON.stringify(infoJSON))*/
    else
      text = document.createTextNode('No value!');/*(JSON.stringify(infoJSON))*/

    const result = document.createElement('p');
    result.appendChild(text);
    save_list.appendChild(result);
    //tee tänne jotain lisää kuva yms
    div.appendChild(save_list);

    updateGame(infoJSON);
    updateMarkers();

  } catch (error) {
    console.log(error.message);
  }
}

//lähettää backendiin minipelikäskyn ja näyttää sen tuloksen modalissa

async function playCoinflip(evt, bet) {
  div.innerHTML = '';
  evt.preventDefault();
  try {
    const response = await fetch(
        `http://127.0.0.1:3000/play_coinflip/${game_id}/${bet}/${evt.submitter.choice}`);
    if (!response.ok) throw new Error('loading games failed');
    const infoJSON = await response.json();
    const save_list = document.createElement('span');
    let text = '';
    if (infoJSON.result == 'Won')
      text = document.createTextNode('You won!');/*(JSON.stringify(infoJSON))*/
    else if (infoJSON.result == 'Lost')
      text = document.createTextNode('You lost!');/*(JSON.stringify(infoJSON))*/
    else
      text = document.createTextNode('No value!');/*(JSON.stringify(infoJSON))*/
    const result = document.createElement('p');
    result.appendChild(text);
    save_list.appendChild(result);
    //tee tänne jotain lisää kuva yms
    div.appendChild(save_list);

    updateGame(infoJSON);
    updateMarkers();

  } catch (error) {
    console.log(error.message);
  }
}

//kutsutaan kun pelaaja löytää kentältä coinflip-goalin; näyttää modalin jolla
//pelaaja päättää millä panoksella pelaa tai jättää pelin pelaamatta.
//Jos pelaaja haluaa pelata, lähetetään backendiin käsky,
// eli playCoinflip() kutsutaan

function coinflip() {
  // Open the modal when the button is clicked
  //nappula dicegamen hyväksymiselle
  div.innerHTML = '';

  const btn3 = document.createElement('input');
  const btn4 = document.createElement('input');
  btn3.type = 'submit';
  btn4.type = 'submit';
  //btn3.addEventListener('click', playCoinflip);
  //btn4.addEventListener('click', playCoinflip);
  //btn3.innerText = 'Tails';
  //btn4.innerText = 'Heads';
  btn3.choice = 'T';
  btn4.choice = 'H';
  btn3.value = 'Tails';
  btn4.value = 'Heads';
  const btn5 = document.createElement('button');
  btn5.innerText = 'No';
  btn5.addEventListener('click', () => dialog.close());

  const form = document.createElement('form');
  const bet = document.createElement('input');

  form.appendChild(bet);
  form.appendChild(btn3);
  form.appendChild(btn4);
  form.addEventListener('submit', (evt) => {
    evt.preventDefault();
    playCoinflip(evt, bet.value);
  });

  bet.type = 'number';
  bet.min = '1';
  bet.max = stats.gas_left;
  const text = document.createTextNode(
      'Shady squirrel offers you to play Coin Toss! Place your bet, if you want to play.');
  const h2 = document.createElement('h2');
  h2.appendChild(text);
  div.appendChild(h2);
  div.appendChild(form);

  div.appendChild(btn5);

  dialog.showModal();
}

// aloitetaan peli tällä, kysytään halutaanko aloittaa uusi peli vai haetaanko uusi muistista// kesken
startGameBtn.addEventListener('click', startGame);

async function startGame() {

  div.innerHTML = '';

//buttons for  starting new game or loading saved game
  const btn1 = document.createElement('button');
  btn1.innerText = 'Load game';
  const btn2 = document.createElement('button');
  btn2.innerText = 'Start new game';

  btn2.addEventListener('click', () => {
    getName();
  });

  btn1.addEventListener('click', getSavedGames);

  div.appendChild(btn1);
  div.appendChild(btn2);

  dialog.showModal();
}

//luo modalin joka pyytää pelaajan nimeä'; kutsutaan kun aloitetaan uusi peli
async function getName() {
  div.innerHTML = '';
  const h = document.createElement('h2');
  const text = document.createTextNode('Insert player name');
  h.appendChild(text);
  div.appendChild(h);

  const nameForm = document.createElement('form');
  const inputText = document.createElement('input');
  const submitBtn = document.createElement('input');
  inputText.type = 'text';
  submitBtn.type = 'submit';
  nameForm.appendChild(inputText);
  nameForm.appendChild(submitBtn);
  nameForm.addEventListener('submit', (evt) => {
    evt.preventDefault();
    screen_name = inputText.value;
    game_id = 0;
//tänne jotain?
    getStartInfo();
  });
  div.appendChild(nameForm);
}

//hakee tiedot backendistä pelin aloitukseen, jos game_id=0, niin backend
// luo uuden tallennuksen tietokantaan pelaajalle. ks.
async function getStartInfo() {
  try {
    const response = await fetch(
        `http://127.0.0.1:3000/startGame/${game_id}/${screen_name}`);
    if (!response.ok) throw new Error('start failed');
    const infoJSON = await response.json();
    game_id = infoJSON.g_id;
    visited_heliports = infoJSON.visited_heliports;
    connected_heliports = infoJSON.connected_heliports;
    heliports_in_range = infoJSON.heliports_in_range;
    stats = infoJSON.stats;
    updateGame(infoJSON);
    updateMarkers();
    /*
    }
*/
    dialog.close();
  } catch
      (e) {

  }
}

//asettaa karttaan merkit värikoodattuna ja tietoja niiden popuppiin
function updateMarkers() {
  airportMarkers.clearLayers();
  let in_range_ICAO = [];
  let visited_ICAO = [];

  for (const heliport of visited_heliports) {
    visited_ICAO += heliport.location;

  }
  for (const heliport of heliports_in_range) {
    in_range_ICAO += heliport.ident;
  }

  for (const heliport of connected_heliports) {
    if (!in_range_ICAO.includes(heliport.ident)) {
      let mark = L.marker([
        parseFloat(heliport.latitude_deg),
        parseFloat(heliport.longitude_deg)]);//.addTo(map);
      airportMarkers.addLayer(mark);

      const popupContent = document.createElement('div');
      const h4 = document.createElement('h4');
      h4.innerHTML = heliport.name;
      popupContent.append(h4);
      //const p = document.createElement('p');
      //p.innerHTML = `Distance ${heliport.distance}km`;
      //popupContent.append(p);
      mark.bindPopup(popupContent);

      if (heliport.ident == stats.location) {
        mark._icon.style.filter = 'hue-rotate(120deg)';

        mark.bindPopup(
            `You are here: <b>${heliport.name}</b>`);
        mark.openPopup();
      }//-120=vihreä, 120=punertava, 0=sininen, -300=violetti

      else if (visited_ICAO.includes(heliport.ident)) {
        mark._icon.style.filter = 'hue-rotate(-150deg)';
      }

    }
  }
  // asettelee kartalle värikoodatut merkit kenttien kohdalle jotka
  // ovat pelaajan ulottuvilla
  placeInRangeMarks();

}

// tätä kutsutaan aina ylemmän updateMarkers()-funktion kanssa, selkeyden vuoksi
// erillisenä funktiona. Asettelee kartalle ulottuvilla olevien kenttien merkit
// värikoodattuna sekä merkkien popupin tiedot
//
function placeInRangeMarks() {
  let in_range_ICAO = [];
  let visited_ICAO = [];

  for (const heliport of visited_heliports) {
    visited_ICAO += heliport.location;

  }
  for (const heliport of heliports_in_range) {
    in_range_ICAO += heliport.ident;
  }

  for (const heliport of heliports_in_range) {

    let mark = L.marker([
      parseFloat(heliport.latitude_deg),
      parseFloat(heliport.longitude_deg)]);//.addTo(map);
    airportMarkers.addLayer(mark);

    const popupContent = document.createElement('div');
    const h4 = document.createElement('h4');
    h4.innerHTML = heliport.name;
    popupContent.append(h4);

    //const p = document.createElement('p');
    //p.innerHTML = `Distance ${heliport.distance}km`;
    //popupContent.append(p);
    mark.bindPopup(popupContent);

    if (visited_ICAO.includes(heliport.ident)) {
      mark._icon.style.filter = 'hue-rotate(-120deg)';
      if (in_range_ICAO.includes(heliport.ident)) {
        mark._icon.style.filter = 'hue-rotate(-120deg)';
        const divPortInfo = document.createElement('div');
        const visitText = document.createTextNode('Heliport has been visited');
        const p = document.createElement('p');
        p.appendChild(visitText);
        divPortInfo.appendChild((p));

        const distText = document.createTextNode(
            `Flight consumes ${heliport.distance_from_player.toFixed(
                1)} pine cones`);
        const p2 = document.createElement('p');
        p2.appendChild(distText);
        divPortInfo.appendChild(p2);

        popupContent.appendChild(divPortInfo);

        const goButton = document.createElement('button');
        goButton.classList.add('button');
        goButton.innerHTML = 'Fly here';
        popupContent.append(goButton);

        goButton.addEventListener('click', function() {
          moveTo(heliport.range_index);
        });
      }
      //-120=vihreä, 120=punertava, 0=sininen, -300=violetti
    } else if (in_range_ICAO.includes(heliport.ident)) {
      mark._icon.style.filter = 'hue-rotate(-300deg)';

      const divPortInfo = document.createElement('div');
      const distText = document.createTextNode(
          `Flight consumes ${heliport.distance_from_player.toFixed(
              1)} pine cones`);
      const p2 = document.createElement('p');
      p2.appendChild(distText);
      divPortInfo.appendChild(p2);

      popupContent.appendChild(divPortInfo);

      const goButton = document.createElement('button');
      goButton.classList.add('button');
      goButton.innerHTML = 'Fly here';
      popupContent.append(goButton);

      goButton.addEventListener('click', function() {
        moveTo(heliport.range_index);
      });
    }
  }
}

//hoitelee pelaajan siirrot
async function moveTo(location) {
  try {
    const response = await fetch(
        `
      http://127.0.0.1:3000/moveTo/${game_id}/${location}`);
    if (!response.ok) throw new Error('move failed');
    const infoJSON = await response.json();
    //dialog.close();
    updateGame(infoJSON);
    updateMarkers();
  } catch
      (e) {

  }
}

//kutsutaan kun halutaan päivittää pelaajan tietoja sivulla, eli on liikuttu,
// pelattu peli, ladattu peli tai aloitettu uusi. Ei päivitä karttaa
function updateGame(infoJSON) {
  visited_heliports = infoJSON.visited_heliports;
  heliports_in_range = infoJSON.heliports_in_range;
  stats = infoJSON.stats;
  const cur_loc = document.getElementById('current-location');
  cur_loc.innerHTML = 'Purple: in range and unvisited / Green: in range and visited ';
  const info = document.getElementById('info');
  info.innerHTML = ' Blue: out of range and unvisited / Yellow: out of range and visited';
  const info3 = document.getElementById('info3');
  info3.innerHTML = 'Red: Player location';
  const in_range = document.getElementById('in-range');
  in_range.innerHTML = heliports_in_range.length;
  const conesEle = document.getElementById('cones-left');
  conesEle.innerHTML = `Pine cones left: ${stats.gas_left}`;
  const scoreEle = document.getElementById('score');
  scoreEle.innerHTML = `Score: ${stats.score}`;
  const p_name = document.getElementById('player-name');
  p_name.innerHTML = `Player name: ${stats.screen_name}`;
  const consumed = document.getElementById('cones-consumed');
  consumed.innerHTML = `Cones consumed: ${stats.gas_consumed}`;
  const rounds = document.getElementById('turns');
  rounds.innerHTML = `Turns played: ${stats.turns}`;

  const event = document.getElementById('event');

  if (infoJSON.goal != false) {

    switch (infoJSON.goal.name) {
      case 'Blackjack':
        //ei toimintoa
        break;
      case 'Coinflip':
        coinflip();
        break;
      case 'Dicegame':
        dicegame();
        break;
      case 'Breakdown':
        console.log(
            `You have had a  ${infoJSON.goal.name}, you lose  ${infoJSON.goal.target_value} pines cones `);
        event.innerHTML = `You have had a  ${infoJSON.goal.name}, you lose  ${infoJSON.goal.target_value} pines cones`;
        break;
      case 'Great':
        showWinModal();
        break;
      default:
        console.log(
            `You have found ${infoJSON.goal.name} stash of pine cones, gained ${infoJSON.goal.target_value}`);
        showWinModal();
    }
  } else {
    event.innerHTML = 'No goal found ';
  }

  if (heliports_in_range.length ==0) {
    showGameOverModal();

  } else {

  }
}

//näyttää pelaajalle modalin, jos kentältä on löytynyt pelin päämäärä
function showWinModal(evt) {
  //tee tähän jotain kun peli voitetaan.
  div.innerHTML = '';
  const text = document.createTextNode(
      'You have found The Mega Cone! Congrats!');
  const p = document.createElement('p');
  const button = document.createElement('button');
  button.innerHTML = 'Show Highscores';
  updateHighscores();

  button.addEventListener('click', showHighscores);
  p.appendChild(text);
  div.appendChild(p);
  div.appendChild(button);

  dialog.showModal();
}

//näyttää pelaajalle modalin, jos kentältä on löytynyt pelin päämäärä/ns.afrikan tähti
function showGameOverModal(evt) {
  //tee tähän jotain kun peli voitetaan.
  div.innerHTML = '';
  const text = document.createTextNode(
      `You're out of pine cones! Game over!`);
  const p = document.createElement('p');

  p.appendChild(text);
  div.appendChild(p);

  dialog.showModal();
}

//päivittää highscore:n tietokantaan, jos pelaajalla on suuremmat pisteet
//kuin tietokannan listassa olevalla
async function updateHighscores() {
  div.innerHTML = '';
  try {

    const response = await fetch(
        `http://127.0.0.1:3000/update_highscores/${game_id}`);
    if (!response.ok) throw new Error('loading games failed');

  } catch (e) {
    console.log(e);
  }

}

// hakee highscore-tiedot backendistä, jonka lisäksi luo
// modalin highscore:ista ja näyttää sen pelaajalle
async function showHighscores() {
  div.innerHTML = '';
  try {

    const response = await fetch(
        `http://127.0.0.1:3000/get_highscores`);
    if (!response.ok) throw new Error('loading games failed');
    const highscores = await response.json();
    const container = document.createElement('div');
    const h_text = document.createElement('h1');
    h_text.appendChild(document.createTextNode('High Scores'));
    div.appendChild(h_text);

    for (let i = 0; i < Math.min(8, highscores.length); i++) {

      const highscoreElement = document.createElement('div');
      highscoreElement.className = 'highscore-item';

      const nameElement = document.createElement('span');
      nameElement.className = 'name';
      nameElement.textContent = `${i + 1}. ${highscores[i].screen_name}:`;

      const scoreElement = document.createElement('span');
      scoreElement.className = 'score';
      scoreElement.textContent = `${highscores[i].score}`;

      highscoreElement.appendChild(nameElement);
      highscoreElement.appendChild(scoreElement);

      container.appendChild(highscoreElement);
      div.appendChild(container);

    }
  } catch (e) {
  }
  dialog.appendChild(div);
  dialog.showModal();

}
/*
//music player
let audioPlayer = document.getElementById('musicPlayer');
let playPauseButton = document.getElementById('playPauseButton');

let currentTrackIndex = 0;
let tracks = [
  'vaporwave1.mp3',
];

// ekan raidan valinta
audioPlayer.src = tracks[currentTrackIndex];

playPauseButton.addEventListener('click', function() {
  if (audioPlayer.paused) {
    audioPlayer.play();
    playPauseButton.textContent = 'Pause';
  } else {
    audioPlayer.pause();
    playPauseButton.textContent = 'Play';
  }
});

audioPlayer.addEventListener('ended', function() {

  currentTrackIndex = (currentTrackIndex + 1) % tracks.length;

  audioPlayer.src = tracks[currentTrackIndex];

  audioPlayer.volume = 0;
  audioPlayer.play();

  let fadeInterval = setInterval(function() {
    audioPlayer.volume += 0.1;
    if (audioPlayer.volume >= 1) {
      audioPlayer.volume = 1;
      clearInterval(fadeInterval);
    }
  }, 500);
});
*/