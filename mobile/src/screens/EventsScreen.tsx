import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, Image, TextInput, ActivityIndicator } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { fetchEvents } from "../api";
import { imageUrl } from "../api";

export default function EventsScreen() {
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const nav = useNavigation<any>();

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchEvents(search || undefined);
      setList(Array.isArray(data) ? data : []);
    } catch {
      setList([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [search]);

  const formatDate = (d: string | null) => {
    if (!d) return "";
    try {
      const dt = new Date(d);
      return dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return d;
    }
  };

  const renderItem = ({ item }: { item: any }) => {
    const pic = item.images?.[0]?.image_url || imageUrl(item.images?.[0]?.image) || imageUrl(item.cover);
    return (
      <TouchableOpacity
        style={styles.row}
        onPress={() => nav.navigate("EventDetail", { slug: item.slug })}
      >
        {pic ? (
          <Image source={{ uri: pic }} style={styles.thumb} />
        ) : (
          <View style={[styles.thumb, styles.thumbPlaceholder]}>
            <Text style={styles.thumbText}>{item.title?.charAt(0) || "E"}</Text>
          </View>
        )}
        <View style={styles.rowText}>
          <Text style={styles.title}>{item.title}</Text>
          <Text style={styles.date}>{formatDate(item.event_date)}</Text>
          {item.location ? <Text style={styles.meta}>📍 {item.location}</Text> : null}
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.search}
        placeholder="Search events..."
        placeholderTextColor="#666"
        value={search}
        onChangeText={setSearch}
      />
      {loading ? (
        <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />
      ) : (
        <FlatList
          data={list}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<Text style={styles.empty}>No events found</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  search: {
    backgroundColor: "#1a1a1c",
    borderWidth: 1,
    borderColor: "#2a2a2c",
    borderRadius: 8,
    padding: 12,
    margin: 16,
    color: "#fff",
    fontSize: 16,
  },
  list: { padding: 16, paddingTop: 0 },
  loader: { flex: 1, justifyContent: "center" },
  empty: { color: "#666", textAlign: "center", marginTop: 24 },
  row: {
    flexDirection: "row",
    backgroundColor: "#1a1a1c",
    padding: 12,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "#2a2a2c",
  },
  thumb: { width: 80, height: 80, borderRadius: 8 },
  thumbPlaceholder: { backgroundColor: "#2a2a2c", justifyContent: "center", alignItems: "center" },
  thumbText: { color: "#D8B57A", fontSize: 28, fontWeight: "700" },
  rowText: { marginLeft: 14, flex: 1, justifyContent: "center" },
  title: { color: "#fff", fontSize: 16, fontWeight: "600" },
  date: { color: "#D8B57A", fontSize: 13, marginTop: 4 },
  meta: { color: "#888", fontSize: 12, marginTop: 2 },
});
