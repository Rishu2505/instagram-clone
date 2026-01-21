import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Post {
  id: string;
  user_id: string;
  username: string;
  profile_pic?: string;
  caption?: string;
  media: { uri: string; type: string }[];
  likes_count: number;
  comments_count: number;
  is_liked: boolean;
  created_at: string;
}

export default function FeedScreen() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [currentMediaIndex, setCurrentMediaIndex] = useState<{ [key: string]: number }>({});
  const router = useRouter();

  useEffect(() => {
    loadFeed();
  }, []);

  const loadFeed = async () => {
    try {
      const token = await AsyncStorage.getItem('authToken');
      const response = await axios.get(`${API_URL}/api/feed`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPosts(response.data);
    } catch (error) {
      console.error('Error loading feed:', error);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadFeed();
  }, []);

  const handleLike = async (postId: string, isLiked: boolean) => {
    try {
      const token = await AsyncStorage.getItem('authToken');
      if (isLiked) {
        await axios.delete(`${API_URL}/api/posts/${postId}/like`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } else {
        await axios.post(
          `${API_URL}/api/posts/${postId}/like`,
          {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }

      setPosts((prevPosts) =>
        prevPosts.map((post) =>
          post.id === postId
            ? {
                ...post,
                is_liked: !isLiked,
                likes_count: isLiked ? post.likes_count - 1 : post.likes_count + 1,
              }
            : post
        )
      );
    } catch (error) {
      console.error('Error liking post:', error);
    }
  };

  const handleNextMedia = (postId: string, mediaLength: number) => {
    setCurrentMediaIndex((prev) => ({
      ...prev,
      [postId]: ((prev[postId] || 0) + 1) % mediaLength,
    }));
  };

  const handlePrevMedia = (postId: string, mediaLength: number) => {
    setCurrentMediaIndex((prev) => ({
      ...prev,
      [postId]: ((prev[postId] || 0) - 1 + mediaLength) % mediaLength,
    }));
  };

  const renderPost = ({ item }: { item: Post }) => {
    const currentIndex = currentMediaIndex[item.id] || 0;
    const currentMedia = item.media[currentIndex];

    return (
      <View style={styles.postContainer}>
        <View style={styles.postHeader}>
          <View style={styles.userInfo}>
            {item.profile_pic ? (
              <Image source={{ uri: item.profile_pic }} style={styles.avatar} />
            ) : (
              <View style={[styles.avatar, styles.avatarPlaceholder]}>
                <Ionicons name="person" size={24} color="#999" />
              </View>
            )}
            <Text style={styles.username}>{item.username}</Text>
          </View>
        </View>

        <View style={styles.mediaContainer}>
          <Image
            source={{ uri: currentMedia.uri }}
            style={styles.media}
            resizeMode="cover"
          />
          {item.media.length > 1 && (
            <>
              <TouchableOpacity
                style={[styles.navButton, styles.navButtonLeft]}
                onPress={() => handlePrevMedia(item.id, item.media.length)}
              >
                <Ionicons name="chevron-back" size={24} color="#fff" />
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.navButton, styles.navButtonRight]}
                onPress={() => handleNextMedia(item.id, item.media.length)}
              >
                <Ionicons name="chevron-forward" size={24} color="#fff" />
              </TouchableOpacity>
              <View style={styles.indicator}>
                <Text style={styles.indicatorText}>
                  {currentIndex + 1} / {item.media.length}
                </Text>
              </View>
            </>
          )}
        </View>

        <View style={styles.postActions}>
          <View style={styles.leftActions}>
            <TouchableOpacity onPress={() => handleLike(item.id, item.is_liked)}>
              <Ionicons
                name={item.is_liked ? 'heart' : 'heart-outline'}
                size={28}
                color={item.is_liked ? '#ed4956' : '#000'}
              />
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton}>
              <Ionicons name="chatbubble-outline" size={28} color="#000" />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.postInfo}>
          {item.likes_count > 0 && (
            <Text style={styles.likes}>{item.likes_count} likes</Text>
          )}
          {item.caption && (
            <Text style={styles.caption}>
              <Text style={styles.captionUsername}>{item.username}</Text> {item.caption}
            </Text>
          )}
          {item.comments_count > 0 && (
            <Text style={styles.viewComments}>View all {item.comments_count} comments</Text>
          )}
        </View>
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0095f6" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Instagram</Text>
      </View>

      <FlatList
        data={posts}
        renderItem={renderPost}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="images-outline" size={80} color="#ccc" />
            <Text style={styles.emptyText}>No posts yet</Text>
            <Text style={styles.emptySubtext}>Follow users to see their posts</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#dbdbdb',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  postContainer: {
    marginBottom: 16,
  },
  postHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    marginRight: 12,
  },
  avatarPlaceholder: {
    backgroundColor: '#f0f0f0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  username: {
    fontSize: 14,
    fontWeight: '600',
  },
  mediaContainer: {
    width: '100%',
    height: 400,
    backgroundColor: '#000',
    position: 'relative',
  },
  media: {
    width: '100%',
    height: '100%',
  },
  navButton: {
    position: 'absolute',
    top: '50%',
    marginTop: -20,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 20,
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  navButtonLeft: {
    left: 8,
  },
  navButtonRight: {
    right: 8,
  },
  indicator: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  indicatorText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  postActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 12,
  },
  leftActions: {
    flexDirection: 'row',
  },
  actionButton: {
    marginLeft: 16,
  },
  postInfo: {
    paddingHorizontal: 12,
  },
  likes: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  caption: {
    fontSize: 14,
    lineHeight: 18,
  },
  captionUsername: {
    fontWeight: '600',
  },
  viewComments: {
    color: '#999',
    fontSize: 14,
    marginTop: 4,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
    color: '#666',
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
});