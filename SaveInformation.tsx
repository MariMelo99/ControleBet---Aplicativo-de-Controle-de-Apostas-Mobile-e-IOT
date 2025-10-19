import AsyncStorage from '@react-native-async-storage/async-storage';
 
 
const usuarios = {
  admin: {
    senha: '12345'
  }
};
 
 
const meta = {
  nome: 'PlayStation 5',
  valor: 4500
};
 
const horasApostando = {
  sem1: 6,
  sem2: 4,
  sem3: 5,
  sem4: 3
};

const logUsuarios = {}
 
export async function SaveInformation() {
    await AsyncStorage.setItem('usuarios', JSON.stringify(usuarios));
    await AsyncStorage.setItem('meta', JSON.stringify(meta));
    await AsyncStorage.setItem('horasApostando', JSON.stringify(horasApostando));
    await AsyncStorage.setItem('logUsuarios', JSON.stringify(logUsuarios));
};