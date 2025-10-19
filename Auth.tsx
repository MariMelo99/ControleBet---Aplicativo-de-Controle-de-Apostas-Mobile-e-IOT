import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from './App'; 

export function useNavigationHandler() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  const navi = async (destination: keyof RootStackParamList) => {
    try {
      const user = await AsyncStorage.getItem('@user');
      
      // Permitir navegação livre para Login e Cadastro
      if (destination === 'Login' || destination === 'Cadastro') {
        navigation.navigate(destination);
        return;
      }
      
      // Para outras rotas, verificar autenticação
      if (user) {
        navigation.navigate(destination);
      } else {
        console.log('Usuário não autenticado, redirecionando para Login');
        navigation.navigate('Login');
      }
    } catch (error) {
      console.error('Erro de navegação:', error);
      navigation.navigate('Login');
    }
  };

  return { navi };
}

// Função para mostrar log de usuários (para debug)
export const mostrarLogUsuarios = async () => {
  try {
    const dados = await AsyncStorage.getItem('@usuariosLogados');
    const usuarios = dados ? JSON.parse(dados) : [];
    console.log('=== LOG DE USUÁRIOS ===');
    console.log('Total de usuários logados:', usuarios.length);
    usuarios.forEach((usuario: any, index: number) => {
      console.log(`${index + 1}. ${usuario.usuario} - ${usuario.dataLogin}`);
    });
    return usuarios;
  } catch (error) {
    console.error('Erro ao mostrar log de usuários:', error);
    return [];
  }
};

// Função para salvar usuário no log
export const salvarUsuario = async (usuario: string) => {
  try {
    const dados = await AsyncStorage.getItem('@usuariosLogados');
    let usuarios = dados ? JSON.parse(dados) : [];
    
    // Criar entrada do log com timestamp
    const logEntry = {
      usuario,
      dataLogin: new Date().toISOString(),
      timestamp: Date.now()
    };
    
    // Verificar se já existe esse usuário hoje
    const hoje = new Date().toDateString();
    const jaLogouHoje = usuarios.find((u: any) => 
      u.usuario === usuario && 
      new Date(u.dataLogin).toDateString() === hoje
    );
    
    if (!jaLogouHoje) {
      usuarios.push(logEntry);
      // Manter apenas os últimos 50 logs
      if (usuarios.length > 50) {
        usuarios = usuarios.slice(-50);
      }
      await AsyncStorage.setItem('@usuariosLogados', JSON.stringify(usuarios));
      console.log(`Usuário ${usuario} salvo no log de acesso`);
    }
  } catch (error) {
    console.error('Erro ao salvar usuário no log:', error);
  }
};

// Função para verificar se usuário está autenticado
export const verificarAutenticacao = async (): Promise<boolean> => {
  try {
    const user = await AsyncStorage.getItem('@user');
    return user !== null;
  } catch (error) {
    console.error('Erro ao verificar autenticação:', error);
    return false;
  }
};

// Função para fazer logout
export const logout = async () => {
  try {
    await AsyncStorage.removeItem('@user');
    console.log('Logout realizado com sucesso');
  } catch (error) {
    console.error('Erro ao fazer logout:', error);
    throw error;
  }
};

// Função para obter usuário atual
export const obterUsuarioAtual = async () => {
  try {
    const userData = await AsyncStorage.getItem('@user');
    return userData ? JSON.parse(userData) : null;
  } catch (error) {
    console.error('Erro ao obter usuário atual:', error);
    return null;
  }
};