import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar } from 'expo-status-bar';

// Imports dos componentes
import { SaveInformation } from './SaveInformation';
import { verificarAutenticacao } from './Auth';
import Login from './Pages/Login';
import Cadastro from './Pages/Cadastro';
import Home from './Pages/Home';
import Meta from './Pages/Meta';
import Horas from './Pages/Horas';

// Definição dos tipos de navegação
export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Cadastro: undefined;
  Meta: undefined;
  Horas: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Inicializar dados padrão
        await SaveInformation();
        
        // Verificar autenticação
        const authenticated = await verificarAutenticacao();
        setIsAuthenticated(authenticated);
        
        // Simular loading para melhor UX
        setTimeout(() => {
          setIsLoading(false);
        }, 1000);
      } catch (error) {
        console.error('Erro ao inicializar app:', error);
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []);

  // Tela de loading
  if (isLoading) {
    return (
      <View style={{ 
        flex: 1, 
        justifyContent: 'center', 
        alignItems: 'center', 
        backgroundColor: '#2D2D2D' 
      }}>
        <ActivityIndicator size="large" color="#F2F0E6" />
      </View>
    );
  }

  return (
    <>
      <NavigationContainer>
        <Stack.Navigator 
          initialRouteName={isAuthenticated ? "Home" : "Login"}
          screenOptions={{
            headerShown: false,
            animation: 'slide_from_right',
          }}
        >
          <Stack.Screen 
            name='Login' 
            component={Login} 
            options={{ 
              headerShown: false,
              gestureEnabled: false 
            }}
          />
          <Stack.Screen 
            name='Cadastro' 
            component={Cadastro} 
            options={{ 
              headerShown: false 
            }}
          />
          <Stack.Screen 
            name='Home' 
            component={Home} 
            options={{ 
              headerShown: false,
              gestureEnabled: false 
            }}
          />
          <Stack.Screen 
            name='Horas' 
            component={Horas} 
            options={{ 
              headerShown: false 
            }}
          />
          <Stack.Screen 
            name='Meta' 
            component={Meta} 
            options={{ 
              headerShown: false 
            }}
          />
        </Stack.Navigator>
      </NavigationContainer>
      <StatusBar style="light" backgroundColor="#2D2D2D" />
    </>
  );
}