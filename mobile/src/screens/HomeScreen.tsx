import React from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { useNavigation } from "@react-navigation/native";

export default function HomeScreen() {
  const nav = useNavigation<any>();

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Global Designer Hub</Text>
      <Text style={styles.subtitle}>Discover designers, collections & events</Text>
      <View style={styles.cards}>
        <TouchableOpacity style={styles.card} onPress={() => nav.navigate("Designers")}>
          <Text style={styles.cardTitle}>Designers</Text>
          <Text style={styles.cardSub}>Browse designer profiles</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.card} onPress={() => nav.navigate("Collections")}>
          <Text style={styles.cardTitle}>Collections</Text>
          <Text style={styles.cardSub}>View fashion collections</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.card} onPress={() => nav.navigate("Events")}>
          <Text style={styles.cardTitle}>Events</Text>
          <Text style={styles.cardSub}>Shows & pop-up events</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 24, paddingTop: 48 },
  title: { fontSize: 28, fontWeight: "700", color: "#fff", marginBottom: 8 },
  subtitle: { fontSize: 16, color: "#999", marginBottom: 32 },
  cards: { gap: 16 },
  card: {
    backgroundColor: "#1a1a1c",
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#2a2a2c",
  },
  cardTitle: { fontSize: 18, fontWeight: "600", color: "#D8B57A" },
  cardSub: { fontSize: 14, color: "#888", marginTop: 4 },
});
