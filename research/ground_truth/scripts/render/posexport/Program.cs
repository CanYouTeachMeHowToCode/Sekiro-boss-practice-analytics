// Local research tool (never committed with game data): the model posed by an animation, by linear blend skinning.
// Usage: posexport <chr .chrbnd.dcx> <chr .anibnd.dcx> <out dir> <animation id> <frame>...
// Writes <out>/<stem>_a<id>_f<frame>.bin: float32 x,y,z per vertex, in meshexport's vertex order.
using System.Numerics;
using SoulsFormats;
using SoulsAssetPipeline.Animation;

var chr = BND4.Read(args[0]); var ani = BND4.Read(args[1]);
if (Environment.GetEnvironmentVariable("LIST") is string pat && pat.Length > 0)
{
    foreach (var f in ani.Files.Where(f => f.Name.Contains(pat))) Console.WriteLine($"{f.ID} {f.Name} {f.Bytes.Length}");
    Console.WriteLine($"{ani.Files.Count} files; names with 'a0': " + string.Join(" ", ani.Files.Select(f => Path.GetFileName(f.Name)).Where(n => n.StartsWith("a")).Select(n => n.Substring(0, 4)).Distinct()));
    return;
}
var outDir = Directory.CreateDirectory(args[2]).FullName; var id = args[3];
var flverFile = chr.Files.First(f => f.Name.ToLower().EndsWith(".flver"));
var flver = FLVER2.Read(flverFile.Bytes); var stem = Path.GetFileNameWithoutExtension(flverFile.Name);

// FLVER bones: bind pose in model space
int nb = flver.Bones.Count; var bind = new Matrix4x4[nb];
for (int i = 0; i < nb; i++)
{
    var b = flver.Bones[i];
    var local = Matrix4x4.CreateScale(b.Scale) * Matrix4x4.CreateRotationX(b.Rotation.X) * Matrix4x4.CreateRotationZ(b.Rotation.Z)
              * Matrix4x4.CreateRotationY(b.Rotation.Y) * Matrix4x4.CreateTranslation(b.Translation);
    bind[i] = b.ParentIndex >= 0 ? local * bind[b.ParentIndex] : local;
}

// HKX skeleton and animation
var comp = ani.Files.First(f => f.Name.ToLower().EndsWith(".compendium")).Bytes;
HKX Fake(string suffix) => HKX.GenFakeFromTagFile(ani.Files.First(f => f.Name.ToLower().EndsWith(suffix)).Bytes, comp);
T Obj<T>(HKX h) => h.DataSection.Objects.OfType<T>().First();
var skel = Obj<HKX.HKASkeleton>(Fake("skeleton.hkx")); int nh = (int)skel.Bones.Size;
var hName = new string[nh]; var hParent = new int[nh]; var hRef = new NewBlendableTransform[nh];
for (int i = 0; i < nh; i++)
{
    dynamic bone = skel.Bones[i]; hName[i] = bone.Name.GetString(); hParent[i] = skel.ParentIndices[i].data;
    dynamic t = skel.Transforms[i]; Vector4 p = t.Position.Vector, r = t.Rotation.Vector, s = t.Scale.Vector;
    hRef[i] = new NewBlendableTransform(new Vector3(p.X, p.Y, p.Z), new Vector3(s.X, s.Y, s.Z), new Quaternion(r.X, r.Y, r.Z, r.W));
}
Matrix4x4[] HkWorld(Func<int, NewBlendableTransform> local)
{
    var w = new Matrix4x4[nh];
    for (int i = 0; i < nh; i++) { var l = local(i).GetMatrixScale() * local(i).GetMatrix(); w[i] = hParent[i] >= 0 ? l * w[hParent[i]] : l; }
    return w;
}
var h = Fake($"a000_{id}.hkx");
var anim = new HavokAnimationData_SplineCompressed(id, skel, Obj<HKX.HKADefaultAnimatedReferenceFrame>(h),
                                                   Obj<HKX.HKAAnimationBinding>(h), Obj<HKX.HKASplineCompressedAnimation>(h));
var hIndex = Enumerable.Range(0, nh).ToDictionary(i => hName[i], i => i);
var match = flver.Bones.Select(b => hIndex.TryGetValue(b.Name, out var k) ? k : -1).ToArray();

// check: same-named bones at rest, FLVER bind vs HKX reference pose
var refW = HkWorld(i => hRef[i]);
var dev = Enumerable.Range(0, nb).Where(i => match[i] >= 0).Select(i => (bind[i].Translation - refW[match[i]].Translation).Length()).ToList();
Console.WriteLine($"FLVER bones {nb}, HKX bones {nh}, matched by name {dev.Count}; rest-pose distance max {dev.Max():F4}, median {dev.OrderBy(x => x).ElementAt(dev.Count / 2):F4}");
foreach (var m in flver.Meshes.Take(0)) { }
if (Environment.GetEnvironmentVariable("ROOT") == "1")
{
    dynamic rf = Obj<HKX.HKADefaultAnimatedReferenceFrame>(h);
    var list = new List<Vector4>();
    var arr = rf.ReferenceFrameSamples;
    for (int i = 0; i < (int)arr.Size; i++) { dynamic v = arr[i]; list.Add((Vector4)v.Vector); }
    Console.WriteLine($"root motion samples {list.Count} over {anim.Duration:F2} s");
    for (int i = 0; i < list.Count; i += Math.Max(1, list.Count / 12))
        Console.WriteLine($"  t {i * anim.Duration / Math.Max(1, list.Count - 1):F2}s  x {list[i].X:F2} y {list[i].Y:F2} z {list[i].Z:F2} yaw {list[i].W:F2}");
    var last = list[^1]; Console.WriteLine($"  end x {last.X:F2} y {last.Y:F2} z {last.Z:F2} yaw {last.W:F2}");
    return;
}
if (Environment.GetEnvironmentVariable("DEV") == "1")
{
    var wsum = new float[nb]; var wm = Enumerable.Range(0, nb).Select(_ => new HashSet<int>()).ToArray();
    for (int m = 0; m < flver.Meshes.Count; m++)
        foreach (var v in flver.Meshes[m].Vertices)
            for (int k = 0; k < 4; k++) if (v.BoneWeights[k] > 0) { wsum[v.BoneIndices[k]] += v.BoneWeights[k]; wm[v.BoneIndices[k]].Add(m); }
    foreach (var i in Enumerable.Range(0, nb).Where(i => match[i] >= 0).OrderByDescending(i => (bind[i].Translation - refW[match[i]].Translation).Length()).Take(12))
        Console.WriteLine($"{flver.Bones[i].Name,-22} rest distance {(bind[i].Translation - refW[match[i]].Translation).Length():F3}  vertex weight {wsum[i],8:F0}  meshes {string.Join(",", wm[i])}");
    return;
}
if (Environment.GetEnvironmentVariable("CLOTH") == "1")
{
    var use = new Dictionary<int, (float w, HashSet<int> meshes)>();
    for (int m = 0; m < flver.Meshes.Count; m++)
        foreach (var v in flver.Meshes[m].Vertices)
            for (int k = 0; k < 4; k++)
                if (v.BoneWeights[k] > 0 && match[v.BoneIndices[k]] < 0)
                {
                    int bi = v.BoneIndices[k];
                    if (!use.ContainsKey(bi)) use[bi] = (0, new HashSet<int>());
                    use[bi] = (use[bi].w + v.BoneWeights[k], use[bi].meshes); use[bi].meshes.Add(m);
                }
    foreach (var kv in use.OrderByDescending(kv => kv.Value.w).Take(40))
    {
        var chain = new List<string>(); int q = flver.Bones[kv.Key].ParentIndex;
        while (q >= 0 && chain.Count < 6) { chain.Add(flver.Bones[q].Name + (match[q] >= 0 ? "" : "*")); if (match[q] >= 0) break; q = flver.Bones[q].ParentIndex; }
        Console.WriteLine($"{flver.Bones[kv.Key].Name,-28} weight {kv.Value.w,8:F0}  meshes {string.Join(",", kv.Value.meshes)}  parents {string.Join(" < ", chain)}");
    }
    Console.WriteLine($"{use.Count} unmatched bones carry vertices");
    return;
}
if (Environment.GetEnvironmentVariable("SCALES") == "1")
{
    var watch = new[] { "R_Katana", "Sheath_Katana", "Sheath", "R_Hand", "Back_yumi", "R_Yumi", "L_Yumi_shinari_01", "R_Ya", "Yadutu" };
    Console.WriteLine("frame " + string.Join(" ", watch.Select(w => $"{w}({(anim.HkxBoneIndexToTransformTrackMap[hIndex[w]] >= 0 ? "anim" : "ref")})")));
    for (int f = 0; f < anim.FrameCount; f += 6)
        Console.WriteLine($"{f,5} " + string.Join(" ", watch.Select(w => { int i = hIndex[w]; var t = anim.HkxBoneIndexToTransformTrackMap[i] >= 0 ? anim.GetTransformOnFrameByBone(i, f, false) : hRef[i]; return $"{t.Scale.X:F2}"; })));
    return;
}
if (args.Length < 5) return;

// root motion: one 4x4 matrix per animation frame (nearest sample), row-vector convention like the bone matrices
{
    dynamic rf = Obj<HKX.HKADefaultAnimatedReferenceFrame>(h);
    var smp = new List<Vector4>(); var arr = rf.ReferenceFrameSamples;
    for (int i = 0; i < (int)arr.Size; i++) { dynamic v = arr[i]; smp.Add((Vector4)v.Vector); }
    var lines = new List<string>();
    for (int f = 0; f < anim.FrameCount; f++)
    {
        int k = smp.Count < 2 ? 0 : Math.Min(smp.Count - 1, (int)Math.Round(f * anim.FrameDuration / anim.Duration * (smp.Count - 1)));
        var m = smp.Count == 0 ? Matrix4x4.Identity : NewBlendableTransform.FromRootMotionSample(smp[k]).GetMatrix();
        lines.Add(string.Join(",", new[] { m.M11, m.M12, m.M13, m.M14, m.M21, m.M22, m.M23, m.M24, m.M31, m.M32, m.M33, m.M34, m.M41, m.M42, m.M43, m.M44 }
                                     .Select(x => x.ToString("R", System.Globalization.CultureInfo.InvariantCulture))));
    }
    File.WriteAllLines(Path.Combine(outDir, $"{stem}_a{id}_root.csv"), lines);
}
var frames = args.Skip(4).SelectMany(a => a.Contains('-') ? Enumerable.Range(int.Parse(a.Split('-')[0]), int.Parse(a.Split('-')[1]) - int.Parse(a.Split('-')[0]) + 1) : new[] { int.Parse(a) });
foreach (var f0 in frames)
{
    if (f0 >= anim.FrameCount && Environment.GetEnvironmentVariable("SKIP_PAST") == "1") continue;
    int f = Math.Min(f0, anim.FrameCount - 1);
    var aw = HkWorld(i => anim.HkxBoneIndexToTransformTrackMap[i] >= 0 ? anim.GetTransformOnFrameByBone(i, f, false) : hRef[i]);
    // each FLVER bone: its animated world; bones the animation does not have ride rigidly on their parent
    var world = new Matrix4x4[nb];
    for (int i = 0; i < nb; i++)
    {
        int p = flver.Bones[i].ParentIndex;
        if (match[i] >= 0) world[i] = aw[match[i]];
        else if (p >= 0) { Matrix4x4.Invert(bind[p], out var ip); world[i] = bind[i] * ip * world[p]; }
        else world[i] = bind[i];
    }
    var skin = new Matrix4x4[nb];
    for (int i = 0; i < nb; i++) { Matrix4x4.Invert(bind[i], out var ib); skin[i] = ib * world[i]; }
    var cape = new HashSet<int>((Environment.GetEnvironmentVariable("CAPE_MESHES") ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries).Select(int.Parse));
    int sp = Array.FindIndex(flver.Bones.ToArray(), b => b.Name == "Spine2"), lc = Array.FindIndex(flver.Bones.ToArray(), b => b.Name == "L_Clavicle"), rc = Array.FindIndex(flver.Bones.ToArray(), b => b.Name == "R_Clavicle");
    float Heading(Matrix4x4[] w) { var r = w[rc].Translation - w[lc].Translation; return MathF.Atan2(r.Z, r.X); }
    var capeTurn = Matrix4x4.CreateTranslation(-bind[sp].Translation) * Matrix4x4.CreateRotationY(Heading(bind) - Heading(world)) * Matrix4x4.CreateTranslation(world[sp].Translation);
    using var bw = new BinaryWriter(File.Create(Path.Combine(outDir, $"{stem}_a{id}_f{f}.bin")));
    int meshNo = -1;
    foreach (var mesh in flver.Meshes)
    {
        meshNo++;
        foreach (var v in mesh.Vertices)
        {
            if (cape.Contains(meshNo)) { var c = Vector3.Transform(v.Position, capeTurn); bw.Write(c.X); bw.Write(c.Y); bw.Write(c.Z); continue; }
            var pos = Vector3.Zero; float sum = 0;
            for (int k = 0; k < 4; k++)
            {
                float wgt = v.BoneWeights[k]; if (wgt <= 0) continue;
                int bi = v.BoneIndices[k]; if (mesh.BoneIndices.Count > 0 && bi < mesh.BoneIndices.Count && mesh.Dynamic == 0) bi = mesh.BoneIndices[bi];
                pos += wgt * Vector3.Transform(v.Position, skin[bi]); sum += wgt;
            }
            if (sum <= 0) { int bi = v.BoneIndices[0]; pos = Vector3.Transform(v.Position, skin[bi]); } else pos /= sum;
            bw.Write(pos.X); bw.Write(pos.Y); bw.Write(pos.Z);
        }
    }
}
