#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#define ACTION_NONE        0
#define ACTION_BOLD        1
#define ACTION_ITALIC      2
#define ACTION_UNDER       3
#define ACTION_UNDO        4
#define ACTION_REDO        5
#define ACTION_SELECT_ALL  6
#define ACTION_DELETE_WORD 7
#define ACTION_DELETE_WORD_BACK 8

#define CHAR_AE_LOWER 0x00E4
#define CHAR_AE_UPPER 0x00C4
#define CHAR_OE_LOWER 0x00F6
#define CHAR_OE_UPPER 0x00D6
#define CHAR_UE_LOWER 0x00FC
#define CHAR_UE_UPPER 0x00DC
#define CHAR_SS       0x00DF

#define TRIE_SIZE 256

typedef struct TrieNode {
    struct TrieNode *children[TRIE_SIZE];
    bool is_end;
    char *word;
    float frequency;         // Frequency of this exact word
    float max_subtree_freq;  // Max frequency in this node's subtree
} TrieNode;

TrieNode *root = NULL;

TrieNode *create_node() {
    TrieNode *node = (TrieNode *)calloc(1, sizeof(TrieNode));
    node->frequency = -1.0f;
    node->max_subtree_freq = -1.0f;
    return node;
}

void trie_insert(const char *word, float frequency) {
    if (!root) root = create_node();
    TrieNode *curr = root;
    
    // Path list to update max_subtree_freq later
    TrieNode *path[1024];
    int path_len = 0;
    
    for (int i = 0; word[i]; i++) {
        uint8_t idx = (uint8_t)tolower(word[i]);
        if (!curr->children[idx]) {
            curr->children[idx] = create_node();
        }
        path[path_len++] = curr;
        curr = curr->children[idx];
    }
    path[path_len++] = curr;

    curr->is_end = true;
    if (!curr->word) curr->word = strdup(word);
    
    if (frequency > curr->frequency) {
        curr->frequency = frequency;
    }

    // Update max_subtree_freq along the path
    for (int i = 0; i < path_len; i++) {
        if (frequency > path[i]->max_subtree_freq) {
            path[i]->max_subtree_freq = frequency;
        }
    }
}

typedef struct {
    char *word;
    float score;
} SearchResult;

// collect_ranked_with_pruning
void collect_ranked_words(TrieNode *node, SearchResult *top_results, int *num_results, int max_results, float min_threshold) {
    if (!node || node->max_subtree_freq <= min_threshold) return;

    if (node->is_end && node->frequency > min_threshold) {
        // Insert into top results
        int pos = -1;
        for (int i = 0; i < *num_results; i++) {
            if (node->frequency > top_results[i].score) {
                pos = i;
                break;
            }
        }
        
        if (pos != -1 || *num_results < max_results) {
            if (pos == -1) pos = *num_results;
            int move_cnt = (*num_results < max_results) ? (*num_results - pos) : (max_results - 1 - pos);
            if (move_cnt > 0) memmove(&top_results[pos+1], &top_results[pos], move_cnt * sizeof(SearchResult));
            top_results[pos].word = node->word;
            top_results[pos].score = node->frequency;
            if (*num_results < max_results) (*num_results)++;
        }
    }

    // Update threshold based on the current 10th best result
    float current_min = (*num_results == max_results) ? top_results[max_results-1].score : -1.0f;

    for (int i = 0; i < TRIE_SIZE; i++) {
        if (node->children[i] && node->children[i]->max_subtree_freq > current_min) {
            collect_ranked_words(node->children[i], top_results, num_results, max_results, current_min);
            // Re-update current_min after each child
            if (*num_results == max_results) current_min = top_results[max_results-1].score;
        }
    }
}

int search_trie_ranked(const char *prefix, char **results, int max_results) {
    if (!root || !prefix || !*prefix) return 0;
    
    TrieNode *curr = root;
    for (int i = 0; prefix[i]; i++) {
        uint8_t idx = (uint8_t)tolower(prefix[i]);
        if (!curr->children[idx]) return 0;
        curr = curr->children[idx];
    }

    SearchResult top_results[max_results];
    int num_results = 0;
    
    collect_ranked_words(curr, top_results, &num_results, max_results, -2.0f);

    for (int i = 0; i < num_results; i++) {
        results[i] = strdup(top_results[i].word);
    }
    
    return num_results;
}

void clear_trie(TrieNode *node) {
    if (!node) return;
    for (int i = 0; i < TRIE_SIZE; i++) {
        if (node->children[i]) clear_trie(node->children[i]);
    }
    if (node->word) free(node->word);
    free(node);
}

void trie_reset() {
    clear_trie(root);
    root = NULL;
}

uint32_t map_to_german(int32_t key_code, int32_t modifiers) {
    bool alt = (modifiers & 0x1);
    bool shift = (modifiers & 0x2);
    if (!alt) return 0;
    switch (key_code) {
        case 'a': case 'A': return shift ? CHAR_AE_UPPER : CHAR_AE_LOWER;
        case 'o': case 'O': return shift ? CHAR_OE_UPPER : CHAR_OE_LOWER;
        case 'u': case 'U': return shift ? CHAR_UE_UPPER : CHAR_UE_LOWER;
        case 's': case 'S': return CHAR_SS;
        default: return 0;
    }
}

int32_t check_shortcut(int32_t key_code, int32_t modifiers) {
    bool ctrl = (modifiers & 0x4);
    bool shift = (modifiers & 0x2);
    if (ctrl) {
        switch (key_code) {
            case 'b': case 'B': return ACTION_BOLD;
            case 'i': case 'I': return ACTION_ITALIC;
            case 'u': case 'U': return ACTION_UNDER;
            case 'z': case 'Z': return shift ? ACTION_REDO : ACTION_UNDO;
            case 'y': case 'Y': return ACTION_REDO;
            case 'a': case 'A': return ACTION_SELECT_ALL;
            case 65535: case 119: case 'd': case 'D': return ACTION_DELETE_WORD;
            case 8: case 22: return ACTION_DELETE_WORD_BACK; // Backspace is often 8 or 22
            default: return ACTION_NONE;
        }
    }
    return ACTION_NONE;
}
