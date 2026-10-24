import { useEffect, useState } from 'react';
import { Alert, AppState, StyleSheet, Text, View, TextInput, Pressable, ScrollView, Platform } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import { normalizeSecret, decodeBase32, totp } from './totp.mjs';
const KEY = 'laboratorio-2fa-secret';
export default function App() {
  const [secret,setSecret] = useState(''), [input,setInput] = useState(''), [now,setNow] = useState(() => Date.now());
  const [error,setError] = useState(''), [ready,setReady] = useState(Platform.OS === 'web');
  useEffect(() => {
    if (Platform.OS === 'web') return;
    SecureStore.getItemAsync(KEY).then(value => { if (value) setSecret(normalizeSecret(value)); })
      .catch(() => setError('No fue posible recuperar la semilla.')).finally(() => setReady(true));
  }, []);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()),250);
    const listener = AppState.addEventListener('change', state => { if (state === 'active') setNow(Date.now()); });
    return () => { clearInterval(timer); listener.remove(); };
  }, []);
  const remaining = 30 - Math.floor(now/1000)%30, code = secret ? totp(secret,now/1000) : '------';
  async function save() {
    try {
      const value = normalizeSecret(input);
      if (decodeBase32(value).length < 16) throw new Error('Usa una semilla de al menos 128 bits.');
      if (Platform.OS !== 'web') await SecureStore.setItemAsync(KEY,value,{keychainAccessible:SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY});
      setSecret(value); setInput(''); setError('');
    } catch (e) { setError(e.message); }
  }
  async function forget() {
    try { if (Platform.OS !== 'web') await SecureStore.deleteItemAsync(KEY); setSecret(''); setError(''); }
    catch { setError('No fue posible borrar la semilla.'); }
  }
  function confirmForget() {
    if (Platform.OS === 'web') { if (window.confirm('¿Eliminar la semilla? Conserva tus códigos de respaldo.')) forget(); }
    else Alert.alert('Eliminar cuenta local','Conserva tus códigos de respaldo.',[{text:'Cancelar',style:'cancel'},{text:'Eliminar',style:'destructive',onPress:forget}]);
  }
  return <ScrollView style={s.screen} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled"><StatusBar style="light" />
    <Text style={s.eyebrow}>LABORATORIO 2FA</Text><Text style={s.title}>Authenticator</Text><Text style={s.description}>Tus códigos se calculan en este dispositivo, incluso en modo avión.</Text>
    <View style={s.card}><Text style={s.label}>CÓDIGO DE VERIFICACIÓN</Text><Text style={s.code} accessibilityLabel={`Código ${code.split('').join(' ')}`}>{code.slice(0,3)} {code.slice(3)}</Text><View style={s.track}><View style={[s.progress,{width:`${remaining/30*100}%`}]} /></View><Text style={s.description}>Se renueva en {remaining} s</Text><Text style={s.eyebrow}>HMAC-SHA1 · 6 DÍGITOS</Text></View>
    {!secret && <View><Text style={s.heading}>Agregar tu cuenta</Text><Text style={s.description}>Pega la semilla Base32 o la URI otpauth del backend.</Text><TextInput accessibilityLabel="Semilla Base32 o URI otpauth" style={s.input} value={input} onChangeText={setInput} autoCapitalize="none" autoCorrect={false} placeholder="Semilla Base32" placeholderTextColor="#81959d" secureTextEntry /><Pressable accessibilityRole="button" disabled={!ready} style={s.button} onPress={save}><Text style={s.buttonText}>{ready ? 'Guardar cuenta' : 'Cargando…'}</Text></Pressable></View>}
    {secret && <Pressable accessibilityRole="button" style={s.secondary} onPress={confirmForget}><Text style={s.light}>Eliminar cuenta del dispositivo</Text></Pressable>}
    {!!error && <Text accessibilityRole="alert" style={s.error}>{error}</Text>}
    {Platform.OS === 'web' && <Text style={s.description}>Vista de escritorio: semilla solo en memoria. En Android se guarda con SecureStore.</Text>}
    <Text style={s.footer}>RFC 6238 · Implementación académica desde cero</Text></ScrollView>;
}
const s = StyleSheet.create({screen:{flex:1,backgroundColor:'#0c1318'},content:{padding:28,paddingTop:70,maxWidth:620,width:'100%',alignSelf:'center'},eyebrow:{color:'#a8efc5',letterSpacing:2,fontSize:11,marginBottom:18},title:{color:'#eef5f4',fontSize:38,fontWeight:'700'},description:{color:'#a4b6bd',fontSize:15,lineHeight:23,marginVertical:12},card:{backgroundColor:'#151f27',padding:24,borderRadius:22,borderWidth:1,borderColor:'#2b3b45',marginVertical:30},label:{color:'#a4b6bd',fontSize:11,letterSpacing:2},code:{color:'#a8efc5',fontSize:48,fontWeight:'700',fontVariant:['tabular-nums'],textAlign:'center',marginVertical:25},track:{height:5,backgroundColor:'#2b3b45',borderRadius:5},progress:{height:5,borderRadius:5,backgroundColor:'#a8efc5'},heading:{color:'#eef5f4',fontSize:22,fontWeight:'600'},input:{color:'#eef5f4',borderWidth:1,borderColor:'#58717e',borderRadius:10,padding:16,marginVertical:12},button:{backgroundColor:'#a8efc5',padding:17,borderRadius:10,alignItems:'center'},buttonText:{color:'#10261a',fontWeight:'700'},secondary:{padding:16,borderWidth:1,borderColor:'#58717e',borderRadius:10,alignItems:'center'},light:{color:'#eef5f4'},error:{color:'#ffb3b3',marginTop:20},footer:{color:'#81959d',marginTop:40,fontSize:11,textAlign:'center'}});
