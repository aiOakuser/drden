import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, ScrollView, Image, ActivityIndicator } from "react-native";
import { useRoute, RouteProp } from "@react-navigation/native";
import { fetchEvent } from "../api";
import { imageUrl } from "../api";

type Params = { EventDetail: { slug: string } };

export default function EventDetailScreen() {
  const route = useRoute<RouteProp<Params, "EventDetail">>();
  const slug = route.params?.slug;
  const [event, setEvent] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchEvent(slug);
        if (!cancelled) setEvent(data);
      } catch {
        if (!cancelled) setEvent(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) return <ActivityIndicator size="large" color="#D8B57A" style={styles.loader} />;
  if (!event) return <Text style={styles.empty}>Event not found</Text>;

  const cover = event.images?.[0]?.image_url || imageUrl(event.images?.[0]?.image) || imageUrl(event.cover);
  const formatDate = (d: string | null) => {
    if (!d) return "";
    try {
      return new Date(d).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
    } catch {
      return d;
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {cover ? (
        <Image source={{ uri: cover }} style={styles.cover} />
      ) : (
        <View style={[styles.cover, styles.coverPlaceholder]}>
          <Text style={styles.coverLetter}>{event.title?.charAt(0) || "E"}</Text>
        </View>
      )}
      <Text style={styles.title}>{event.title}</Text>
      <Text style={styles.date}>{formatDate(event.event_date)}</Text>
      {event.end_date && event.end_date !== event.event_date && (
        <Text style={styles.meta}>– {formatDate(event.end_date)}</Text>
      )}
      {event.venue ? <Text style={styles.meta}>📍 {event.venue}</Text> : null}
      {event.location ? <Text style={styles.meta}>{event.location}</Text> : null}
      {event.description ? <Text style={styles.desc}>{event.description}</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0E0E0F" },
  content: { padding: 20, paddingBottom: 40 },
  loader: { flex: 1, justifyContent: "center", backgroundColor: "#0E0E0F" },
  empty: { color: "#666", textAlign: "center", marginTop: 48 },
  cover: { width: "100%", height: 220, borderRadius: 12, backgroundColor: "#1a1a1c" },
  coverPlaceholder: { justifyContent: "center", alignItems: "center" },
  coverLetter: { color: "#D8B57A", fontSize: 64, fontWeight: "700" },
  title: { color: "#fff", fontSize: 24, fontWeight: "700", marginTop: 16 },
  date: { color: "#D8B57A", fontSize: 15, marginTop: 4 },
  meta: { color: "#888", fontSize: 14, marginTop: 4 },
  desc: { color: "#ccc", fontSize: 15, marginTop: 16, lineHeight: 22 },
});
