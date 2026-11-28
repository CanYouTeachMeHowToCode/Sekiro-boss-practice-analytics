public static class Diag
{
    public static void Run(SoulsFormats.FLVER2 flver, System.Collections.Generic.HashSet<string> hkxBones)
    {
        for (int m = 0; m < flver.Meshes.Count; m++)
        {
            var mesh = flver.Meshes[m];
            var w = new System.Collections.Generic.Dictionary<int, float>();
            foreach (var v in mesh.Vertices)
                for (int k = 0; k < 4; k++) { if (v.BoneWeights[k] > 0) { w.TryGetValue(v.BoneIndices[k], out var x); w[v.BoneIndices[k]] = x + v.BoneWeights[k]; } }
            var total = System.Linq.Enumerable.Sum(w.Values);
            var top = System.Linq.Enumerable.Take(System.Linq.Enumerable.OrderByDescending(w, kv => kv.Value), 3);
            var txt = string.Join(", ", System.Linq.Enumerable.Select(top, kv => $"{flver.Bones[kv.Key].Name}{(hkxBones.Contains(flver.Bones[kv.Key].Name) ? "" : "*")} {kv.Value / total:P0}"));
            System.Console.WriteLine($"mesh {m,2} {mesh.Vertices.Count,6} v  {flver.Materials[mesh.MaterialIndex].Name,-20} {txt}");
        }
    }
}
