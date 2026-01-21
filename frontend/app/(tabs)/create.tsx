import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ScrollView,
  TextInput,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface MediaItem {
  uri: string;
  type: 'image' | 'video';
}

export default function CreateScreen() {
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [caption, setCaption] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const router = useRouter();

  const requestPermissions = async () => {
    const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
    const { status: mediaStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (cameraStatus !== 'granted' || mediaStatus !== 'granted') {
      Alert.alert(
        'Permissions Required',
        'Please grant camera and media library permissions to create posts.'
      );
      return false;
    }
    return true;
  };

  const pickImage = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    if (media.length >= 10) {
      Alert.alert('Limit Reached', 'You can only add up to 10 media items');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images', 'videos'],
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      const base64Uri = `data:${asset.type === 'video' ? 'video/mp4' : 'image/jpeg'};base64,${asset.base64}`;
      
      setMedia([...media, {
        uri: base64Uri,
        type: asset.type === 'video' ? 'video' : 'image',
      }]);
    }
  };

  const takePhoto = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    if (media.length >= 10) {
      Alert.alert('Limit Reached', 'You can only add up to 10 media items');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      const base64Uri = `data:image/jpeg;base64,${asset.base64}`;
      
      setMedia([...media, {
        uri: base64Uri,
        type: 'image',
      }]);
    }
  };

  const removeMedia = (index: number) => {
    setMedia(media.filter((_, i) => i !== index));
  };

  const handlePost = async () => {
    if (media.length === 0) {
      Alert.alert('No Media', 'Please add at least one photo or video');
      return;
    }

    setIsUploading(true);
    try {
      const token = await AsyncStorage.getItem('authToken');
      await axios.post(
        `${API_URL}/api/posts`,
        {
          caption,
          media,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      Alert.alert('Success', 'Post created successfully!');
      setMedia([]);
      setCaption('');
      router.push('/(tabs)/feed');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create post');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="close" size={32} color="#000" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>New Post</Text>
        <TouchableOpacity onPress={handlePost} disabled={isUploading || media.length === 0}>
          <Text
            style={[
              styles.postButton,
              (isUploading || media.length === 0) && styles.postButtonDisabled,
            ]}
          >
            {isUploading ? 'Posting...' : 'Post'}
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {media.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="images-outline" size={80} color="#ccc" />
            <Text style={styles.emptyText}>Add photos or videos</Text>
            <View style={styles.buttonContainer}>
              <TouchableOpacity style={styles.addButton} onPress={takePhoto}>
                <Ionicons name="camera" size={24} color="#fff" />
                <Text style={styles.addButtonText}>Take Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.addButton} onPress={pickImage}>
                <Ionicons name="images" size={24} color="#fff" />
                <Text style={styles.addButtonText}>Choose from Gallery</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <>
            <ScrollView horizontal style={styles.mediaScroll} showsHorizontalScrollIndicator={false}>
              {media.map((item, index) => (
                <View key={index} style={styles.mediaItem}>
                  <Image source={{ uri: item.uri }} style={styles.mediaImage} />
                  <TouchableOpacity
                    style={styles.removeButton}
                    onPress={() => removeMedia(index)}
                  >
                    <Ionicons name="close-circle" size={24} color="#fff" />
                  </TouchableOpacity>
                  {item.type === 'video' && (
                    <View style={styles.videoIndicator}>
                      <Ionicons name="play" size={32} color="#fff" />
                    </View>
                  )}
                </View>
              ))}
              {media.length < 10 && (
                <TouchableOpacity style={styles.addMoreButton} onPress={pickImage}>
                  <Ionicons name="add" size={32} color="#0095f6" />
                </TouchableOpacity>
              )}
            </ScrollView>

            <View style={styles.captionContainer}>
              <TextInput
                style={styles.captionInput}
                placeholder="Write a caption..."
                placeholderTextColor="#999"
                value={caption}
                onChangeText={setCaption}
                multiline
                maxLength={2200}
              />
            </View>

            <View style={styles.buttonContainer}>
              <TouchableOpacity style={styles.secondaryButton} onPress={takePhoto}>
                <Ionicons name="camera" size={20} color="#0095f6" />
                <Text style={styles.secondaryButtonText}>Add Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.secondaryButton} onPress={pickImage}>
                <Ionicons name="images" size={20} color="#0095f6" />
                <Text style={styles.secondaryButtonText}>Add from Gallery</Text>
              </TouchableOpacity>
            </View>
          </>
        )}
      </ScrollView>

      {isUploading && (
        <View style={styles.uploadingOverlay}>
          <View style={styles.uploadingContainer}>
            <ActivityIndicator size="large" color="#0095f6" />
            <Text style={styles.uploadingText}>Creating post...</Text>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#dbdbdb',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  postButton: {
    color: '#0095f6',
    fontSize: 16,
    fontWeight: '600',
  },
  postButtonDisabled: {
    opacity: 0.5,
  },
  content: {
    flex: 1,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 80,
  },
  emptyText: {
    fontSize: 18,
    color: '#666',
    marginTop: 16,
    marginBottom: 32,
  },
  buttonContainer: {
    paddingHorizontal: 24,
    width: '100%',
  },
  addButton: {
    backgroundColor: '#0095f6',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
  },
  addButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  mediaScroll: {
    padding: 16,
  },
  mediaItem: {
    width: 150,
    height: 150,
    marginRight: 12,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  mediaImage: {
    width: '100%',
    height: '100%',
  },
  removeButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 12,
  },
  videoIndicator: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    marginTop: -16,
    marginLeft: -16,
  },
  addMoreButton: {
    width: 150,
    height: 150,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#0095f6',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
  },
  captionContainer: {
    padding: 16,
  },
  captionInput: {
    fontSize: 16,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderWidth: 1,
    borderColor: '#0095f6',
    borderRadius: 8,
    marginBottom: 12,
  },
  secondaryButtonText: {
    color: '#0095f6',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
  },
  uploadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  uploadingContainer: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 12,
    alignItems: 'center',
  },
  uploadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#000',
  },
});