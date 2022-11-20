function switch_to_select() {
    //gradioApp().querySelector('#selectbox').querySelector('textarea').value = gradioApp().querySelector('.px-3.py-1').innerHTML;
    gradioApp().querySelectorAll('#tab_b2p_interface')[0].querySelectorAll('button')[0].click();
    return gradioApp().querySelector('.px-3.py-1').innerHTML;
}