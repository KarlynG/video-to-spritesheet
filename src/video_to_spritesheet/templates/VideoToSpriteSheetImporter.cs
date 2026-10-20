#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.U2D.Sprites;
using UnityEngine;

// Requires Unity 2022.3+ and the com.unity.2d.sprite package.
// Keep one copy of this helper in your Unity project.
public static class VideoToSpriteSheetImporter
{
    [Serializable] private class RectData { public int x, y, w, h; }
    [Serializable] private class PivotData { public float x, y; }
    [Serializable] private class PageData { public string image; public int width, height; }
    [Serializable] private class FrameData
    {
        public int index, page;
        public string name;
        public RectData rect;
    }
    [Serializable] private class ImportData
    {
        public int schema_version;
        public string engine, resample;
        public float pixels_per_unit, frame_rate;
        public PivotData pivot;
        public PageData[] pages;
        public FrameData[] frames;
    }

    [MenuItem("Tools/Video to Sprite Sheet/Import Selected Unity JSON")]
    public static void ImportSelected()
    {
        try
        {
            string jsonPath = AssetDatabase.GetAssetPath(Selection.activeObject);
            if (!jsonPath.StartsWith("Assets/", StringComparison.Ordinal) || Path.GetFileName(jsonPath) != "unity.json")
                throw new InvalidOperationException("Select the generated unity.json inside your Assets folder.");
            ImportData data = JsonUtility.FromJson<ImportData>(File.ReadAllText(jsonPath));
            Validate(data);
            string folder = Path.GetDirectoryName(jsonPath).Replace('\\', '/');
            string clipPath = folder + "/animation.anim";
            UnityEngine.Object existingAsset = AssetDatabase.LoadMainAssetAtPath(clipPath);
            if (existingAsset != null && !(existingAsset is AnimationClip))
                throw new InvalidOperationException("animation.anim is occupied by another asset type.");
            if (existingAsset != null && !EditorUtility.DisplayDialog("Replace animation clip?",
                    "This will replace the generated animation in " + clipPath, "Replace", "Cancel"))
                return;

            // Check every source texture before modifying import settings.
            for (int p = 0; p < data.pages.Length; p++)
            {
                string path = folder + "/" + data.pages[p].image;
                if (!(AssetImporter.GetAtPath(path) is TextureImporter))
                    throw new InvalidOperationException("Missing texture: " + path);
            }

            var sprites = new Dictionary<string, Sprite>();
            for (int p = 0; p < data.pages.Length; p++)
            {
                PageData page = data.pages[p];
                string path = folder + "/" + page.image;
                var importer = (TextureImporter)AssetImporter.GetAtPath(path);
                importer.textureType = TextureImporterType.Sprite;
                importer.spriteImportMode = SpriteImportMode.Multiple;
                importer.spritePixelsPerUnit = data.pixels_per_unit;
                importer.alphaIsTransparency = true;
                importer.mipmapEnabled = false;
                importer.npotScale = TextureImporterNPOTScale.None;
                importer.textureCompression = TextureImporterCompression.Uncompressed;
                importer.filterMode = data.resample == "nearest" ? FilterMode.Point : FilterMode.Bilinear;
                importer.maxTextureSize = Mathf.Clamp(Mathf.NextPowerOfTwo(Mathf.Max(page.width, page.height)), 32, 16384);
                importer.SaveAndReimport();

                var factory = new SpriteDataProviderFactories();
                factory.Init();
                var provider = factory.GetSpriteEditorDataProviderFromObject(importer);
                if (provider == null)
                    throw new InvalidOperationException("Sprite data provider missing. Install the 2D Sprite package.");
                provider.InitSpriteEditorDataProvider();
                var old = provider.GetSpriteRects().ToDictionary(rect => rect.name, rect => rect.spriteID);
                SpriteRect[] rects = data.frames.Where(frame => frame.page == p).Select(frame => new SpriteRect
                {
                    name = frame.name,
                    spriteID = old.ContainsKey(frame.name) ? old[frame.name] : GUID.Generate(),
                    rect = new Rect(frame.rect.x, frame.rect.y, frame.rect.w, frame.rect.h),
                    alignment = SpriteAlignment.Custom,
                    pivot = new Vector2(data.pivot.x, data.pivot.y)
                }).ToArray();
                provider.SetSpriteRects(rects);
                var ids = provider.GetDataProvider<ISpriteNameFileIdDataProvider>();
                if (ids == null)
                    throw new InvalidOperationException("Sprite name/ID provider is unavailable in this Editor version.");
                ids.SetNameFileIdPairs(rects.Select(rect => new SpriteNameFileIdPair(rect.name, rect.spriteID)));
                provider.Apply();
                importer.SaveAndReimport();
                foreach (Sprite sprite in AssetDatabase.LoadAllAssetsAtPath(path).OfType<Sprite>())
                    sprites.Add(sprite.name, sprite);
            }

            var keys = new ObjectReferenceKeyframe[data.frames.Length + 1];
            for (int i = 0; i < data.frames.Length; i++)
            {
                Sprite sprite;
                if (!sprites.TryGetValue(data.frames[i].name, out sprite))
                    throw new InvalidOperationException("Imported Sprite missing: " + data.frames[i].name);
                keys[i] = new ObjectReferenceKeyframe { time = i / data.frame_rate, value = sprite };
            }
            // Preserve the final frame's full duration before the loop returns to frame zero.
            keys[keys.Length - 1] = new ObjectReferenceKeyframe
            {
                time = data.frames.Length / data.frame_rate,
                value = keys[keys.Length - 2].value
            };
            var clip = existingAsset as AnimationClip;
            if (clip == null)
            {
                clip = new AnimationClip();
                AssetDatabase.CreateAsset(clip, clipPath);
            }
            clip.frameRate = data.frame_rate;
            var binding = new EditorCurveBinding { path = "", type = typeof(SpriteRenderer), propertyName = "m_Sprite" };
            AnimationUtility.SetObjectReferenceCurve(clip, binding, keys);
            var settings = AnimationUtility.GetAnimationClipSettings(clip);
            settings.loopTime = true;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();
            Selection.activeObject = clip;
            Debug.Log("Imported " + data.frames.Length + " sprites across " + data.pages.Length + " pages: " + clipPath);
        }
        catch (Exception error)
        {
            Debug.LogException(error);
            EditorUtility.DisplayDialog("Video to Sprite Sheet", error.Message, "OK");
        }
    }

    private static void Validate(ImportData data)
    {
        if (data == null || data.engine != "unity" || data.schema_version != 1 || data.pivot == null ||
            data.pages == null || data.pages.Length == 0 || data.frames == null || data.frames.Length == 0 ||
            !(data.frame_rate > 0) || !(data.pixels_per_unit > 0) ||
            float.IsInfinity(data.frame_rate) || float.IsInfinity(data.pixels_per_unit) ||
            !(data.pivot.x >= 0 && data.pivot.x <= 1 && data.pivot.y >= 0 && data.pivot.y <= 1))
            throw new InvalidOperationException("Invalid generated Unity import descriptor.");
        foreach (PageData page in data.pages)
        {
            if (page == null || String.IsNullOrEmpty(page.image) || Path.GetFileName(page.image) != page.image ||
                page.image.Contains("/") || page.image.Contains("\\") || !page.image.EndsWith(".png", StringComparison.OrdinalIgnoreCase) ||
                page.width < 1 || page.height < 1 || page.width > 16384 || page.height > 16384)
                throw new InvalidOperationException("Invalid sheet filename or dimensions.");
        }
        var names = new HashSet<string>();
        for (int i = 0; i < data.frames.Length; i++)
        {
            FrameData frame = data.frames[i];
            if (frame == null || frame.index != i || frame.page < 0 || frame.page >= data.pages.Length ||
                String.IsNullOrEmpty(frame.name) || !names.Add(frame.name) || frame.rect == null ||
                frame.rect.x < 0 || frame.rect.y < 0 || frame.rect.w < 1 || frame.rect.h < 1)
                throw new InvalidOperationException("Invalid frame name, index, page, or rectangle.");
            PageData page = data.pages[frame.page];
            if ((long)frame.rect.x + frame.rect.w > page.width || (long)frame.rect.y + frame.rect.h > page.height)
                throw new InvalidOperationException("A frame rectangle is outside its sheet.");
        }
    }
}
#endif
